use std::collections::BTreeMap;

use apple_codesign_quick::{
    BundleSigningSettings, ProvisioningProfile, RustCryptoCmsSigner, sign_bundle,
};

use plist::Dictionary;
use rootcause::prelude::*;
use tracing::warn;

use crate::{
    dev::{app_ids::Profile, teams::DeveloperTeam},
    sideload::{
        application::{Application, SpecialApp},
        cert_identity::CertificateIdentity,
    },
};

pub fn required_accessory_entitlement(info: &Dictionary) -> Option<&'static str> {
    let point = info.get("EXAppExtensionAttributes")?.as_dictionary()?
        .get("EXExtensionPointIdentifier")?.as_string()?;
    match point {
        "com.apple.accessory-data-provider" => Some("com.apple.developer.accessory-data-provider"),
        "com.apple.accessory-transport-security" => Some("com.apple.developer.accessory-transport-security"),
        "com.apple.accessory-transport-extension" => Some("com.apple.developer.accessory-transport-extension"),
        _ => None,
    }
}

pub fn verify_accessory_profile(info: &Dictionary, entitlements: &Dictionary) -> Result<(), Report> {
    if let Some(key) = required_accessory_entitlement(info)
        && entitlements.get(key).and_then(plist::Value::as_boolean) != Some(true)
    {
        bail!("Apple profile did not grant Boolean true for {}. Signing stopped; no extension was removed. This does not prove the capability is unavailable to every free account.", key);
    }
    Ok(())
}

pub async fn sign<F, Fut>(
    app: &mut Application,
    cert_identity: &CertificateIdentity,
    main_provisioning_profile: &Profile,
    all_profiles: &mut Vec<(String, Profile, Dictionary)>,
    special: &Option<SpecialApp>,
    team: &DeveloperTeam,
    progress_callback: Option<F>,
) -> Result<(), Report>
where
    F: Fn(f32) -> Fut,
    Fut: Future<Output = ()>,
{
    for extension in app.bundle.app_extensions() {
        if required_accessory_entitlement(&extension.app_info).is_some() {
            let bundle_id = extension.bundle_identifier().ok_or_report()?;
            let (_, _, granted) = all_profiles.iter().find(|(id, _, _)| id == bundle_id)
                .ok_or_else(|| report!("Missing separate provisioning profile for {}", bundle_id))?;
            verify_accessory_profile(&extension.app_info, granted)?;
        }
    }
    let profile = ProvisioningProfile::parse(main_provisioning_profile.encoded_profile.as_ref())?;
    let certificate_chain = cert_identity.profile_to_certificate_chain(&profile)?;

    let signer = RustCryptoCmsSigner::new(
        cert_identity.private_key.clone(),
        cert_identity.certificate.clone(),
        certificate_chain,
    );
    if let Some(callback) = &progress_callback {
        callback(0.4).await;
    }

    let mut entitlements = profile.entitlements().clone();
    if matches!(
        special,
        Some(SpecialApp::SideStoreLc) | Some(SpecialApp::LiveContainer)
    ) {
        let mut keychain_access = vec![plist::Value::String(format!(
            "{}.com.kdt.livecontainer.shared",
            team.team_id
        ))];

        for number in 1..128 {
            keychain_access.push(plist::Value::String(format!(
                "{}.com.kdt.livecontainer.shared.{}",
                team.team_id, number
            )));
        }

        entitlements.insert(
            "keychain-access-groups".to_string(),
            plist::Value::Array(keychain_access.clone()),
        );

        let liveprocess_profile = all_profiles
            .iter_mut()
            .find(|(bundle_id, _, _)| bundle_id.ends_with("LiveProcess"));
        if let Some((_, _, liveprocess_entitlements)) = liveprocess_profile {
            liveprocess_entitlements.insert(
                "keychain-access-groups".to_string(),
                plist::Value::Array(keychain_access),
            );
        } else {
            warn!("Could not find LiveProcess profile");
        }
    }

    let mut settings = BundleSigningSettings::new(&team.team_id, entitlements, Some(&signer));
    settings.embedded_mobileprovision = Some(main_provisioning_profile.encoded_profile.as_ref());

    settings.embedded_mobileprovisions_by_bundle_id = all_profiles
        .iter()
        .map(|(bundle_id, data, _)| (bundle_id.clone(), data.encoded_profile.as_ref()))
        .collect::<BTreeMap<_, _>>();
    settings.entitlements_by_bundle_id = all_profiles
        .iter()
        .map(|(bundle_id, _, entitlements)| (bundle_id.clone(), entitlements.clone()))
        .collect();

    if let Some(callback) = &progress_callback {
        callback(0.5).await;
    }

    Ok(sign_bundle(&app.bundle.bundle_dir, &settings)?)
}

use std::{io::{self, IsTerminal, Write}, path::{Path, PathBuf}};
use idevice::usbmuxd::{UsbmuxdAddr, UsbmuxdConnection};
use isideload::{
    anisette::{AnisetteProvider, remote_v3::RemoteV3AnisetteProvider},
    auth::apple_account::{AppleAccount, TwoFactorCallbackParams, TwoFactorCallbackResponse},
    dev::{app_ids::AppIdsApi, certificates::CertificatesApi, developer_session::DeveloperSession, teams::TeamsApi},
    sideload::{SideloaderBuilder, TeamSelection, bundle::Bundle, builder::MaxCertsBehavior,
        sign::required_accessory_entitlement},
    util::{callbacks::MaxCertsCallbackBox, keyring_storage::KeyringStorage},
};
use rootcause::prelude::*;
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

const SERVICE: &str = "kaspi-probe-signer";
const SERVER: &str = "https://mac-ani.jkcoxson.com";
const PROBE_ID: &str = "site.shrks.kaspiprobe.access";
const SOURCE_SHA256: &str = "3a0598d681a89a8c8c7f59b5af9732581e38becf017571660381884d4ffc37bf";

fn prompt(text: &str) -> Result<String, Report> {
    print!("{text}");
    io::stdout().flush()?;
    let mut value = String::new();
    if io::stdin().read_line(&mut value)? == 0 { bail!("Input closed; operation cancelled."); }
    Ok(value.trim().to_string())
}

fn validate_probe(bundle: &Bundle) -> Result<(), Report> {
    if bundle.bundle_identifier() != Some(PROBE_ID) { bail!("Only the isolated Kaspi Access Probe is supported."); }
    if bundle.app_extensions().len() != 3 { bail!("Expected exactly three intact accessory extensions."); }
    let mut keys = std::collections::BTreeSet::new();
    for extension in bundle.app_extensions() {
        let key = required_accessory_entitlement(&extension.app_info)
            .ok_or_else(|| report!("Unknown extension point; refusing to sign."))?;
        let suffix = match key {
            "com.apple.developer.accessory-data-provider" => "data",
            "com.apple.developer.accessory-transport-security" => "security",
            "com.apple.developer.accessory-transport-extension" => "transport",
            _ => unreachable!(),
        };
        if extension.bundle_identifier() != Some(format!("{PROBE_ID}.{suffix}").as_str()) {
            bail!("Unexpected accessory bundle identifier.");
        }
        if !extension.bundle_dir.starts_with(bundle.bundle_dir.join("Extensions")) {
            bail!("Accessory extensions must retain their original Extensions directory.");
        }
        if !keys.insert(key) { bail!("Duplicate accessory extension role."); }
    }
    Ok(())
}

fn inspect(path: &Path) -> Result<(), Report> {
    if !path.is_file() || path.extension().and_then(|s| s.to_str()) != Some("ipa") {
        bail!("Inspect accepts an IPA file, never an original application directory.");
    }
    let temp = tempfile::tempdir()?;
    let mut archive = zip::ZipArchive::new(std::fs::File::open(path)?)?;
    if archive.len() > 1000 { bail!("Unexpectedly large probe archive."); }
    let mut size = 0u64;
    for index in 0..archive.len() {
        let entry = archive.by_index(index)?;
        size = size.saturating_add(entry.size());
        if size > 64 * 1024 * 1024 || entry.is_symlink() || entry.enclosed_name().is_none() {
            bail!("Unsafe or oversized probe archive.");
        }
    }
    archive.extract(temp.path())?;
    let payload = temp.path().join("Payload");
    let apps = std::fs::read_dir(&payload)?.collect::<Result<Vec<_>, _>>()?;
    let apps: Vec<_> = apps.into_iter().filter(|e| e.path().extension().is_some_and(|s| s == "app")).collect();
    if apps.len() != 1 { bail!("Expected one application in Payload."); }
    let bundle = Bundle::new(apps[0].path())?;
    validate_probe(&bundle)?;
    let extensions: Vec<_> = bundle.app_extensions().iter().map(|extension| {
            serde_json::json!({"bundle_id":extension.bundle_identifier(),
                "directory":"Extensions", "required_entitlement":required_accessory_entitlement(&extension.app_info)})
        }).collect();
    println!("{}", serde_json::json!({"bundle_id":PROBE_ID,"extensions":extensions,
            "extension_count":extensions.len(),"network_used":false,"apple_profile_granted":false,
            "bank_notifications_verified":false}));
    Ok(())
}

fn require_local_interaction() -> Result<(), Report> {
    if std::env::var_os("CI").is_some() || !io::stdin().is_terminal() || !io::stdout().is_terminal() {
        bail!("Apple account actions are disabled in CI and redirected consoles.");
    }
    if std::env::var_os("DEBUG_SENSITIVE").is_some() { bail!("Sensitive debugging must be disabled."); }
    Ok(())
}

async fn authenticate() -> Result<(DeveloperSession, String), Report> {
    require_local_interaction()?;
    let provider = RemoteV3AnisetteProvider::default()?
        .set_url(SERVER)
        .set_serial_number("0".to_string())
        .set_storage(Box::new(KeyringStorage::new(SERVICE.to_string())));
    provider.get_client_info().await?;
    println!("Verified Anisette endpoint. Credentials are sent only to Apple by the authentication library.");
    let email = prompt("Apple ID email: ")?.to_lowercase();
    if !email.contains('@') || email.contains(char::is_whitespace) { bail!("Invalid email."); }
    let password = Zeroizing::new(rpassword::prompt_password("Apple ID password (hidden): ")?);
    let callback = async |params: TwoFactorCallbackParams| {
        if params.unknown { println!("Approve the sign-in on your iPhone, or type d to request a trusted-device code."); }
        let code = Zeroizing::new(rpassword::prompt_password("2FA code (hidden), d for device, q to cancel: ")?);
        let response = match code.trim() {
            "d" => TwoFactorCallbackResponse::SendToDevices,
            "q" => TwoFactorCallbackResponse::Abort,
            value if value.len() == 6 && value.bytes().all(|v| v.is_ascii_digit()) =>
                TwoFactorCallbackResponse::SubmitCode(value.to_string()),
            _ => TwoFactorCallbackResponse::Abort,
        };
        Ok(response)
    };
    let mut account = AppleAccount::builder(&email).anisette_provider(provider)
        .err_429_retries(None).login(password.as_str(), callback).await?;
    drop(password);
    Ok((DeveloperSession::from_account(&mut account).await?, email))
}

async fn account_check() -> Result<(), Report> {
    let (mut session, _) = authenticate().await?;
    let teams = session.list_teams().await?;
    if teams.len() != 1 { bail!("Expected one developer team. No team was selected and no changes were made."); }
    let team = &teams[0];
    let certs = session.list_all_development_certs(team, None).await?;
    let apps = session.list_app_ids(team, None).await?;
    println!("{}", serde_json::json!({"login":true,"certificate_count":certs.len(),
        "available_app_ids":apps.available_quantity,"mutations":false,"bank_notifications_verified":false}));
    Ok(())
}

async fn install_probe(path: PathBuf) -> Result<(), Report> {
    require_local_interaction()?;
    let digest = format!("{:x}", Sha256::digest(std::fs::read(&path)?));
    if digest != SOURCE_SHA256 { bail!("Input does not match the verified, isolated Access Probe build."); }
    inspect(&path)?;
    println!("TEST ONLY. May register four App IDs, a device, profiles and one NEW development certificate.");
    println!("Existing certificates are NEVER revoked. Missing profile permissions stop signing.");
    if prompt("Type INSTALL TEST PROBE to authorize these account changes: ")? != "INSTALL TEST PROBE" {
        bail!("Cancelled; no account changes were made.");
    }
    let mut mux = UsbmuxdConnection::default().await?;
    let devices = mux.get_devices().await?;
    if devices.len() != 1 { bail!("Connect exactly one iPhone by USB; no device was chosen."); }
    let provider = devices[0].to_provider(UsbmuxdAddr::from_env_var()?, SERVICE);
    let (session, email) = authenticate().await?;
    let mut loader = SideloaderBuilder::<MaxCertsCallbackBox>::new(session, email)
        .team_selection(TeamSelection::PromptOnce(|_| None))
        .max_certs_behavior(MaxCertsBehavior::Error)
        .machine_name(SERVICE.to_string())
        .storage(Box::new(KeyringStorage::new(SERVICE.to_string())))
        .build();
    loader.install_app(&provider, path, false,
        None::<fn(f32) -> std::future::Ready<()>>, None).await?;
    println!("Test package installed. Notification reception and background reliability are NOT verified.");
    Ok(())
}

#[tokio::main]
async fn main() {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let _ = isideload::init();
    let args: Vec<_> = std::env::args().skip(1).collect();
    let result = match args.as_slice() {
        [command, path] if command == "inspect" => inspect(Path::new(path)),
        [command] if command == "check-account" => account_check().await,
        [command, path] if command == "install-probe" => install_probe(PathBuf::from(path)).await,
        [] => { println!("Kaspi Probe Signer 0.1.0\nCommands: inspect <IPA>, check-account, install-probe <IPA>\nNo production KaspiDonate integration. No notification success claim."); Ok(()) }
        _ => Err(report!("Unknown command. Passwords, codes, keys and tokens must never be command-line arguments.")),
    };
    if let Err(error) = result { eprintln!("{error}"); std::process::exit(1); }
}

#[cfg(test)]
mod tests {
    use super::*;
    use plist::{Dictionary, Value};
    use isideload::sideload::sign::verify_accessory_profile;

    fn info(point: &str) -> Dictionary {
        let mut attributes = Dictionary::new();
        attributes.insert("EXExtensionPointIdentifier".into(), Value::String(point.into()));
        let mut result = Dictionary::new();
        result.insert("EXAppExtensionAttributes".into(), Value::Dictionary(attributes));
        result
    }

    #[test]
    fn profile_permissions_must_be_boolean_true() {
        for point in ["com.apple.accessory-data-provider", "com.apple.accessory-transport-security", "com.apple.accessory-transport-extension"] {
            let metadata = info(point);
            let key = required_accessory_entitlement(&metadata).unwrap();
            for value in [None, Some(Value::Boolean(false)), Some(Value::String("true".into()))] {
                let mut profile = Dictionary::new();
                if let Some(value) = value { profile.insert(key.into(), value); }
                assert!(verify_accessory_profile(&metadata, &profile).is_err());
            }
            let mut profile = Dictionary::new();
            profile.insert(key.into(), Value::Boolean(true));
            assert!(verify_accessory_profile(&metadata, &profile).is_ok());
        }
    }

    fn fixture(legacy: bool, broken: bool) -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        let mut main = Dictionary::new();
        main.insert("CFBundleIdentifier".into(), Value::String(PROBE_ID.into()));
        plist::to_file_binary(dir.path().join("Info.plist"), &main).unwrap();
        for (name, point) in [("data", "com.apple.accessory-data-provider"), ("security", "com.apple.accessory-transport-security"), ("transport", "com.apple.accessory-transport-extension")] {
            let child = dir.path().join("Extensions").join(format!("{name}.appex"));
            std::fs::create_dir_all(&child).unwrap();
            let mut child_info = info(point);
            child_info.insert("CFBundleIdentifier".into(), Value::String(format!("{PROBE_ID}.{name}")));
            plist::to_file_binary(child.join("Info.plist"), &child_info).unwrap();
        }
        if legacy {
            let child = dir.path().join("PlugIns/Widget.appex");
            std::fs::create_dir_all(&child).unwrap();
            plist::to_file_binary(child.join("Info.plist"), &main).unwrap();
        }
        if broken { std::fs::create_dir_all(dir.path().join("Extensions/Broken.appex")).unwrap(); }
        dir
    }

    #[test]
    fn extensionkit_bundles_remain_in_extensions() {
        let dir = fixture(false, false);
        let bundle = Bundle::new(dir.path().to_path_buf()).unwrap();
        validate_probe(&bundle).unwrap();
        assert_eq!(bundle.app_extensions().len(), 3);
        assert!(dir.path().join("Extensions/transport.appex/Info.plist").is_file());
    }

    #[test]
    fn legacy_and_extensionkit_are_both_discovered() {
        let dir = fixture(true, false);
        let bundle = Bundle::new(dir.path().to_path_buf()).unwrap();
        assert_eq!(bundle.app_extensions().len(), 4);
        assert!(validate_probe(&bundle).is_err());
    }

    #[test]
    fn broken_extensions_are_not_silently_dropped() {
        let dir = fixture(false, true);
        assert!(Bundle::new(dir.path().to_path_buf()).is_err());
    }

    #[test]
    fn inspection_never_accepts_or_removes_an_original_directory() {
        let dir = fixture(false, false);
        assert!(inspect(dir.path()).is_err());
        assert!(dir.path().join("Info.plist").is_file());
        assert!(dir.path().join("Extensions/transport.appex/Info.plist").is_file());
    }

    #[test]
    fn unexpected_child_identifiers_are_rejected() {
        let dir = fixture(false, false);
        let mut bundle = Bundle::new(dir.path().to_path_buf()).unwrap();
        bundle.app_extensions_mut()[0].set_bundle_identifier("another.application");
        assert!(validate_probe(&bundle).is_err());
    }
}

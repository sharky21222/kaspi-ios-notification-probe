import json
import sys


EXPECTED = {
    'AccessProbe': 'site.shrks.kaspiprobe.access',
    'ProbeDataProvider': 'site.shrks.kaspiprobe.access.data',
    'ProbeSecurity': 'site.shrks.kaspiprobe.access.security',
    'ProbeTransport': 'site.shrks.kaspiprobe.access.transport',
}


def validate(settings):
    targets = {item['target']: item['buildSettings'] for item in settings}
    for target, bundle_id in EXPECTED.items():
        actual = targets.get(target, {}).get('PRODUCT_BUNDLE_IDENTIFIER')
        if actual != bundle_id:
            raise ValueError(f'{target}: expected bundle identifier {bundle_id}, got {actual!r}')


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as stream:
        validate(json.load(stream))
    print('PASS application and extension bundle identifiers')

import os, sys, glob, traceback, json

import parse_one


API_DIRECTORY = sys.argv[1]

already_done = {json.load(open(dos)).get('url_dossier_senat') for dos \
                in glob.glob(os.path.join(API_DIRECTORY, '*/viz/procedure.json'))}

for url in sys.stdin:
    print()
    print('======')
    url = url.strip()
    if url in already_done:
        print('  + passed, already done:', url)
        continue

    try:
        parse_one.process(API_DIRECTORY, url, only_promulgated=True)
    except KeyboardInterrupt:
        break
    except Exception as e:
        traceback.print_exc()

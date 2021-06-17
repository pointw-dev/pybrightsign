import sys

setup_file = './setup.py'

version = ''
moded = ''

if len(sys.argv) == 2:
    version = sys.argv[1]


with open(setup_file, 'r') as f:
    lines = f.readlines()

for line in lines:
    if line.startswith('    version='):
        print(line)
        line = f"    version='{version}',\n"
        
    moded += line

if version:
    print(f'New version: {version}')
    with open(setup_file, 'w') as f:
        f.write(moded)
else:
    print('unchanged')


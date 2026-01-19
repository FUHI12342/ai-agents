import argparse

def reverse_string(s):
    return s[::-1]

def main():
    parser = argparse.ArgumentParser(description='Speckit CLI')
    parser.add_argument('--input', required=True, help='Input string')
    parser.add_argument('--output', required=True, help='Output file')
    args = parser.parse_args()
    result = reverse_string(args.input)
    with open(args.output, 'w') as f:
        f.write(result)

if __name__ == '__main__':
    main()
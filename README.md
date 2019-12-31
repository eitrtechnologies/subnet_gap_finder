# Subnet Gap Finder
Utility script to show unused gaps in IP space within a list of networks.

## Background
This script was born out of a need to find unused subnet space within a large,
micro-segmented VPC in AWS. Sorting the subnets and looking for spaces manually
isn't easy on the eyes. The first iteration of this script used a file input
which was accomplished by copying and pasting subnets out of the AWS UI and then
massaging the data to remove the extra information. Once I proved that the logic
worked, I added the functionality necessary to get the subnet information
straight from the source. I hope you find it useful.

## Usage
The script takes *either* the `filename` *or* the `vpcid` argument... not both.
```
usage: subnet_gap_finder.py [-h] [--filename FILENAME] [--loglevel LOGLEVEL]
                            [--vpcid VPC_ID]

Utility script to show unused gaps in IP space within a list of networks.

optional arguments:
  -h, --help            show this help message and exit
  --filename FILENAME, -f FILENAME
                        Path to a file containing a list of IP networks.
                        EITHER "filename" OR "vpcid" IS REQUIRED
  --loglevel LOGLEVEL, -l LOGLEVEL
                        Specify log level as text string: ERROR, WARNING,
                        INFO, DEBUG
  --vpcid VPC_ID, -i VPC_ID
                        ID of a VPC in AWS to query. Subnets will be checked
                        as the list of networks. EITHER "filename" OR "vpcid"
                        IS REQUIRED.
```

### File input
File input expects a newline-separated list of subnets in the file. Any line
containing other text is thrown out, so you don't need to clean up your data too
much.
```
$ python3 subnet_gap_finder.py --filename tests/example.txt
| Gap Start   | Gap End    | Gap CIDRs     |
|-------------+------------+---------------|
| 10.0.6.128  | 10.0.6.255 | 10.0.6.128/25 |
| 10.0.7.32   | 10.0.7.63  | 10.0.7.32/27  |
| 10.0.7.128  | 10.0.7.159 | 10.0.7.128/27 |
```

### VPC ID
VPC mode basically works the same way, with the exception that we can also see
unused space at the end of the last subnet until the end of the VPC address
space. This is (currently) only shown if there aren't any gaps between subnets.
```
$ python3 subnet_gap_finder.py --vpcid vpc-a675b09
| Gap Start   | Gap End     | Gap CIDRs     |
|-------------+-------------+---------------|
| 10.0.8.0    | 10.0.15.255 | 10.0.8.0/21   |
```

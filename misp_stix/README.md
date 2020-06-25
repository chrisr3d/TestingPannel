# Parse Simplified MISP Format

This piece of code is an addon to the STIX test functionality already implemented and released in MISP.

The test functionality uses the STIX export & import scripts to export a MISP event and reimport it from the created STIX file.  
Doing so, we can have a quick look at what is supported in the export & import mapping.

The goal here is not to overwrite this functionality, but to provide an additional visualization of the results of the tests, in order to have an overview of the data created during the export & import process.

### Requirements

- **Python3.6+**
- An access to the MISP instance used to run the tests

### Installation

In order to make this work, simply execute the initiate.sh script:

```
# Using the default path to MISP: /var/www/MISP/app/files/scripts/stixtest/
bash initiate.sh
```
```
# Or using your own MISP path
bash initiate.sh YOUR_PATH_TO_MISP/app/files/scripts/stixtest/
```
The idea here is to create a link of the script directly in the stix test directory.

### Usage

##### Reminder: How to use the stix test functionality
```
# Example of usage to test the STIX2 export & import scripts
cd /var/www/MISP/app/files/scripts/stixtest
/var/www/MISP/venv/bin/python stix2_check.py --withAttachment 1 --eventid 1255 -o indicators
```
With this example, you get 3 test files:
- The initial MISP event in JSON format
- The initial MISP event exported in STIX2 format
- The regenerated MISP event resulting from an import of the STIX2 file

At this point you already got an overview of the data included with a comparison between the initial MISP event and the regenerated one.

#### Getting a simplified view of the data created within the different test files

Once you have the required test files geneated during the execution of the command mention above, you can now visualize the data contained in the 2 MISP events which are supposed to be almost the same (modulo the mapping loss).
```
# Reusing the files generated with the example mentioned above
/var/www/MISP/venv/bin/python parse_simplified_misp_format.py -o test_json_indicators.json -m test_stix2_indicators.json.stix2
```
You get then 2 files providing an overview of all the attributes and objects which are supposed to stay the same before and after the process.  
Another dictionary file provides the mapping of the test files with their corresponding simplified representation.

At the same time, a debugging message is displayed to show the comparison of the attributes and objects saved in the simplifed files.

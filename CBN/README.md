Chronicle CBN Testing
Config Based Normalizer (CBN) allows customers to convert logs from various SIEM log sources to Chronicle UDM proto.
Use this procedure for testing the config file (logstash based) against sample logs.  
Sample log files are provided here for different log types for testing pruposes.

Steps:
1) Choose a sample log file, read a log line from it and convert it to Chronicle proto format here:  
   https://apps.chronicle.security/partner-tools/convert-log-to-proto
   Provide any log type in the log type field -- this is not used for parsing while testing using this tool. 
   Save output to a file (convension is to use .proto as extension) by copying and pasting the results in a file.
2) Write a CBN config file in your own editor (convension is to use .conf as extension) 
   and test it against the log proto file from the step 1:  
   https://apps.chronicle.security/partner-tools/
   
Hint: Use the ‘back’ browser button while iteratively testing, it will save your file selection

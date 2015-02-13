SERVER=http://localhost:8080
URL=$SERVER/api/licensing/trial_register

# Test with good license key
http -f POST $URL system-id='123' license-key='41349500-c5c6-4130-aa57-0d14b408e423' license-type='Named-user' license-quantity=15

# Test with invalid license key

# Test with a system that is already in this stage


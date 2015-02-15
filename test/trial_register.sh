SERVER=http://localhost:8080
URL=$SERVER/api/licensing/trial_register
KEY='c8aabfd4-196d-40c4-bbfd-b5dde9fc4fa6'

# Test with good license key
http -f POST $URL system-id='123' license-key=$KEY license-type='Named-user' license-quantity=15

# Test with invalid license key

# Test with a system that is already in this stage


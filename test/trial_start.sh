SERVER=http://localhost:8080
URL=$SERVER/api/licensing/trial_start
KEY='f4f70cbb-5fd6-423c-b761-0eed65dc32fe'

# Test with good license key
http -f POST $URL system-id='123' license-key=$KEY license-type='Named-user' license-quantity=15

# Test with invalid license key

# Test with a system that is already in this stage


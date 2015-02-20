SERVER=http://localhost:8080
URL=$SERVER/api/trial_start
KEY=$1

# Test with good license key
http -f POST $URL system-id='123' license-key=$KEY license-type='Named-user' license-quantity=15

# Test with invalid license key

# Test with a system that is already in this stage


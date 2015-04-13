SERVER=http://localhost:8080
URL=$SERVER/api/verify

# Test with good license key
http GET $URL?key=$1


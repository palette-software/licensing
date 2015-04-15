SERVER=http://localhost:8080
URL=$SERVER/api/register

# Test with good license key
http -f POST $URL firstname=$1 lastname=$2 email=$3 

# script to test checking of hostname
# usage: check_name.sh hostname

http GET http://localhost:8080/api/check_name hostname=="$1"

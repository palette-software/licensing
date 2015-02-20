SERVER=http://localhost:8080
URL=$SERVER/api/buy_request
KEY=$1

# Legend
# names = ['Field3', 'Field4', 'Field6', 'Field5', 'Field21', \
#          'Field22', 'Field8', 'Field9', \
#          'Field13', 'Field14', 'Field15', 'Field16', 'Field17', 'Field18', \
#          'Field225', \
#          'Field11', 'Field12', 'Field20', 'Field19']
# fields = ['firstname', 'lastname', 'organization', 'email', 'phone', \
#          'palette_type', 'license_type', 'license_cap', \
#          'billing_address_line1', 'billing_address_line2', \
#          'billing_city', 'billing_state', 'billing_zip', \
#          'billing_country', 'alt_billing']
#          'billing_fn', 'billing_ln', 'billing_email', 'billing_phone'


# Test new user
http -f POST $URL Field3='Vahid' Field4='Kowsari' Field6='Test Inc.' Field5='vahid@kowsari.com' Field21='415-509-1645' Field22='' Field8='Self Hosting' Field9='' Field13='Address 1' Field14='Address 2' Field15='City' Field16='State' Field17='Zip' Field18='United States' Field225='False' Field11='' Field12='' Field20='' Field19='' Field7=$KEY

# Test with existing Organization

# Test with existing Website

# Test with existing Subdomain

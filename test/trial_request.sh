SERVER=http://localhost:8080
URL=$SERVER/api/trial

# Legend
#    'fname':'firstname', 'lname':'lastname',$
#    'email':'email',$
#    'text-yui_3_10_1_1_1389902554996_16499-field': 'website',$
#    'radio-yui_3_17_2_1_1407117642911_45717-field':'admin_role',$
#    'radio-yui_3_17_2_1_1426521445942_51014-field':'hosting_type'$

AWS='Your AWS Account with our AMI Image'
VMWARE='Your Data Center with our VMware Image'
PCLOUD='Palette Online'
SUBDOMAIN='test-palette'

# Test new user
#http -f POST $URL Field1='Vahid' Field2='Kowsari' Field3='vahid@kowsari.com' Field6='Test Inc.' Field115='test.com' Field8="$VMWARE" Field9=''

# Test with existing Organization

# Test with existing Website

# Test with existing Subdomain

http -f POST $URL fname='Vahid' lname='Kowsari' email='vahid@kowsari.com' text-yui_3_10_1_1_1389902554996_16499-field='test.com' radio-yui_3_17_2_1_1407117642911_45717-field="Tableau Admin" radio-yui_3_17_2_1_1426521445942_51014-field="$AWS"

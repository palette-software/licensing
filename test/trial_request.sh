SERVER=http://localhost:8080
URL=$SERVER/api/trial_request

# Legend
# Firstname = Field1
# Last Name = Field2
# Email = Field 3
# Organization = Field 6
# Organization Domain = Field 115
# Hosting Type = Field 8
# Subdomain = Field 9

# Test new user
http -f POST $URL Field1='Vahid' Field2='Kowsari' Field3='vahid@kowsari.com' Field6='Test Inc.' Field115='test.com' Field8='Self Hosting' Field9=''

# Test with existing Organization

# Test with existing Website

# Test with existing Subdomain

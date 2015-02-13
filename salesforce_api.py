from simple_salesforce import Salesforce
import config

class SalesforceAPI():
    """
    """
    @classmethod
    def new_opportunity(cls, data):
        """ Create a new Salesforce Opportunity
        """
        name = data.firstname + ' ' + data.lastname

        sf = Salesforce(username=config.SALESFORCE_USERNAME,
                        password=config.SALESFORCE_PASSWORD,
                        security_token=config.SALESFORCE_TOKEN)

        account = sf.query("""SELECT Name, id
                  FROM Account where Name='{0}'""".format(data.organization))
        if account is None or account['totalSize'] == 0:
            account = sf.Account.create({'Name':org, 'Phone':phone})
            print account
            accountid = account['id']
        else:
            accountid = account['records'][0]['Id']

        sf.Opportunity.create({'Name':name, 'AccountId':accountid, \
                              'StageName': data.stage, \
                              'CloseDate': data.expiration_time.isoformat(), \
                              'Palette_License_Key__c': data.key, \
                              'Palette_Server_Time_Zone__c': data.timezone \
                              })

    @classmethod
    def update_opportunity(cls, name, data):
        """ Update a Salesforce Opportunity
        """
        sf = Salesforce(username=config.SALESFORCE_USERNAME,
                        password=config.SALESFORCE_PASSWORD,
                        security_token=config.SALESFORCE_TOKEN)

        opp = sf.query("""SELECT Name, id FROM Opportunity
                          where Name='{0}'""".format(name))
        if opp is not None and opp['totalSize'] == 1:
            oppid = opp['id']
            sf.Opportunity.update(oppid, {'Stage':data.stage})


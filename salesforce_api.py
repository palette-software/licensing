from datetime import datetime
from simple_salesforce import Salesforce

import config

sf = Salesforce(username=config.SALESFORCE_USERNAME,
                password=config.SALESFORCE_PASSWORD,
                security_token=config.SALESFORCE_TOKEN)

class SalesforceAPI():
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """
    @classmethod
    def lookup_account(cls, data):
        """ Lookup an account and return the id
        """
        account = sf.query("""SELECT Name, id
                  FROM Account where Name='{0}'""".format(data.organization))
        if account is None or account['totalSize'] == 0:
            accountid = None
        else:
            accountid = account['records'][0]['Id']
        return accountid

    @classmethod
    def lookup_or_create_account(cls, data):
        """ Lookup or create an account using the supplied data
        """
        accountid = cls.lookup_account(data)
        if accountid is None:
            account = sf.Account.create({'Name':data.organization, \
                                         'Phone':data.phone})
            accountid = account['id']
            print 'Creating Account Name {0} Id {1}'.format(data.organization, \
                                                       accountid)

        return accountid

    @classmethod
    def update_account(cls, data):
        """ Update an account
        """
        accountid = cls.lookup_account(data)
        if accountid is None:
            sf.Account.update(accountid, 
                 {'Name':data.organization, \
                  'Phone':data.phone})
            print 'Updating Account Name {0} Id {1}'.format(data.organization, \
                                                       accountid)


    @classmethod
    def lookup_contact(cls, data):
        """ Lookup a contact
        """
        contact = sf.query("""SELECT Name, id
                  FROM Contact where Firstname='{0}' and Lastname='{1}'"""\
                  .format(data.firstname, data.lastname))
        if contact is None or contact['totalSize'] == 0:
            contactid = None
        else:
            contactid = contact['records'][0]['Id']
        return contactid

    @classmethod
    def lookup_or_create_contact(cls, data):
        """ Lookup or create contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is None:
            contact = sf.Contact.create({'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone})
            contactid = contact['id']
            print 'Creating Contact Name {0} Id {1}'.format(data.firstname, \
                                                            data.lastname, \
                                                            contactid)

        return contactid

    @classmethod
    def update_contact(cls, data):
        """ Update Contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is not None:
            sf.Contact.Update(contactid, {'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone})
            print 'Updating Contact Name {0} {1} Id {1}'.\
                       format(data.firstname, data.lastname, contactid)

    @classmethod
    def new_opportunity(cls, data):
        """ Create a new Salesforce Opportunity
        """
        contactid = cls.lookup_or_create_contact(data)
        accountid = cls.lookup_or_create_account(data)

        name = data.organization + ' ' + \
               data.firstname + ' ' + data.lastname + ' ' +\
               datetime.utcnow().isoformat()

        sf.Opportunity.create({'Name':name, 'AccountId':accountid, \
                              'StageName': data.stage, \
                              'CloseDate': data.expiration_time.isoformat(), \
                              'Palette_License_Key__c': data.key, \
                              'Palette_Server_Time_Zone__c': data.timezone \
                              })

    @classmethod
    def update_opportunity(cls, data):
        """ Update a Salesforce Opportunity
        """
        opp = sf.query("""SELECT Name, id FROM Opportunity
                          where Palette_License_Key__c='{0}'""".\
                          format(data.key))
        print opp
        if opp is not None and opp['totalSize'] == 1:
            oppid = opp['records'][0]['Id']
            sf.Opportunity.update(oppid, 
                 {'StageName':data.stage, \
                  'CloseDate':data.expiration_time.isoformat() \
                 })


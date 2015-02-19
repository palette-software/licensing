from datetime import datetime
import logging
import config

from stage import Stage

from simple_salesforce import Salesforce

logger = logging.getLogger('licensing')

class SalesforceAPI():
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """
    def __init__(self, username, password, security_token):
        """ Initialize the salesforce object
        """
        self.sf = Salesforce(username=username, password=password, \
                             security_token=security_token)

    def lookup_account(self, data):
        """ Lookup an account and return the id
        """
        account = self.sf.query("""SELECT Name, id
                  FROM Account where Name='{0}'""".format(data.organization))
        if account is None or account['totalSize'] == 0:
            accountid = None
        else:
            accountid = account['records'][0]['Id']
        return accountid

    def lookup_or_create_account(self, data):
        """ Lookup or create an account using the supplied data
        """
        accountid = self.lookup_account(data)
        if accountid is None:
            account = self.sf.Account.create({'Name':data.organization, \
                                         'Phone':data.phone})
            accountid = account['id']
            logger.info('Creating Account Name {0} Id {1}'\
                         .format(data.organization, accountid))

        return accountid

    def update_account(self, data):
        """ Update an account
        """
        accountid = self.lookup_account(data)
        if accountid is None:
            self.sf.Account.update(accountid, 
                 {'Name':data.organization, \
                  'Phone':data.phone})
            logger.info('Updating Account Name {0} Id {1}'\
                        .format(data.organization, accountid))

    def lookup_contact(self, data):
        """ Lookup a contact
        """
        contact = self.sf.query("""SELECT Name, id
                  FROM Contact where Firstname='{0}' and Lastname='{1}'"""\
                  .format(data.firstname, data.lastname))
        if contact is None or contact['totalSize'] == 0:
            contactid = None
        else:
            contactid = contact['records'][0]['Id']
        return contactid

    def lookup_or_create_contact(self, data):
        """ Lookup or create contact
        """
        contactid = self.lookup_contact(data)
        if contactid is None:
            contact = self.Contact.create({'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone})
            contactid = contact['id']
            logger.info('Creating Contact Name {0} Id {1}'\
                        .format(data.firstname, data.lastname, contactid))

        return contactid

    def update_contact(self, data):
        """ Update Contact
        """
        contactid = self.lookup_contact(data)
        if contactid is not None:
            self.sf.Contact.Update(contactid, {'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone})
            logger.info('Updating Contact Name {0} {1} Id {1}'.\
                       format(data.firstname, data.lastname, contactid))

    def new_opportunity(self, data):
        """ Create a new Salesforce Opportunity
        """
        contactid = self.lookup_or_create_contact(data)
        accountid = self.lookup_or_create_account(data)

        name = data.organization + ' ' + \
               data.firstname + ' ' + data.lastname + ' ' +\
               datetime.utcnow().isoformat()

        self.sf.Opportunity.create({'Name':name, 'AccountId':accountid, \
                              'StageName': Stage.get_by_id(data.stageid).name, \
                              'CloseDate': data.expiration_time.isoformat(), \
                              'Palette_License_Key__c': data.key, \
                              'Palette_Server_Time_Zone__c': data.timezone \
                              })
        logger.info('Creating new opportunity with Contact '\
                    'Name {0} {1} Account Id {1}'.\
                     format(data.firstname, data.lastname, accountid))

    def update_opportunity(self, data):
        """ Update a Salesforce Opportunity
        """
        opp = self.sf.query("""SELECT Name, id FROM Opportunity
                          where Palette_License_Key__c='{0}'""".\
                          format(data.key))
        if opp is not None and opp['totalSize'] == 1:
            logger.info('Updating opportunity Key {0} Stage {1}'\
                     .format(data.key, Stage.get_by_id(data.stageid).name))

            oppid = opp['records'][0]['Id']
            self.sf.Opportunity.update(oppid,
                 {'StageName':Stage.get_by_id(data.stageid).name, \
                  'CloseDate':data.expiration_time.isoformat() \
                 })


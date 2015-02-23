from datetime import datetime, date
import logging
import config

from stage import Stage
from system import System
from simple_salesforce import Salesforce

logger = logging.getLogger('licensing')

class SalesforceAPI():
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """
    @classmethod
    def lookup_account(cls, data):
        """ Lookup an account and return the id
        """
        sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))

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
            sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
            account = sf.Account.create({'Name':data.organization, \
                                         'Phone':data.phone})
            accountid = account['id']
            logger.info('Creating Account Name {0} Id {1}'\
                         .format(data.organization, accountid))

        return accountid

    @classmethod
    def update_account(cls, data):
        """ Update an account
        """
        accountid = cls.lookup_account(data)
        if accountid is None:
            sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
            sf.Account.update(accountid, 
                 {'Name':data.organization, \
                  'Phone':data.phone})
            logger.info('Updating Account Name {0} Id {1}'\
                        .format(data.organization, accountid))

    @classmethod
    def lookup_contact(cls, data):
        """ Lookup a contact
        """
        sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
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
            sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
            contact = sf.Contact.create({'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone, \
                                         'Admin_Role__c':data.admin_role})
            contactid = contact['id']
            logger.info('Creating Contact Name {0} Id {1}'\
                        .format(data.firstname, data.lastname, contactid))

        return contactid

    @classmethod
    def update_contact(cls, data):
        """ Update Contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is not None:
            sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
            sf.Contact.Update(contactid, {'Firstname':data.firstname, \
                                         'Lastname':data.lastname, \
                                         'Email':data.email, \
                                         'Phone':data.phone, \
                                         'Admin_Role__c':data.admin_role})
            logger.info('Updating Contact Name {0} {1} Id {1}'.\
                       format(data.firstname, data.lastname, contactid))

    @classmethod
    def new_opportunity(cls, data):
        """ Create a new Salesforce Opportunity
        """
        contactid = cls.lookup_or_create_contact(data)
        accountid = cls.lookup_or_create_account(data)

        name = data.organization + ' ' + \
               data.firstname + ' ' + data.lastname + ' ' +\
               datetime.utcnow().strftime('%x %X')

        sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
        sf.Opportunity.create({'Name':name, 'AccountId':accountid, \
                              'StageName': Stage.get_by_id(data.stageid).name, \
                              'CloseDate': data.expiration_time.isoformat(), \
                              'Expiration_Date__c':\
                                    data.expiration_time.isoformat(), \
                              'Palette_License_Key__c': data.key, \
                              'Palette_Server_Time_Zone__c': data.timezone, \
                              'Hosting_Type__c':data.hosting_type, \
                              'AWS_Region__c':data.aws_zone, \
                              'Palette_Cloud_subdomain__c':data.subdomain \
                              })
        logger.info('Creating new opportunity with Contact '\
                    'Name {0} {1} Account Id {1}'.\
                     format(data.firstname, data.lastname, accountid))

    @classmethod
    def update_opportunity(cls, data):
        """ Update a Salesforce Opportunity
        """
        sf = Salesforce(username=System.get_by_key('salesforce_username'), \
                        password=System.get_by_key('salesforce_password'), \
                        security_token=System.get_by_key('salesforce_token'))
        opp = sf.query("""SELECT Name, id FROM Opportunity
                          where Palette_License_Key__c='{0}'""".\
                          format(data.key))
        if opp is not None and opp['totalSize'] == 1:
            logger.info('Updating opportunity Key {0} Stage {1}'\
                     .format(data.key, Stage.get_by_id(data.stageid).name))

            oppid = opp['records'][0]['Id']
            sf.Opportunity.update(oppid,
                 {'StageName':Stage.get_by_id(data.stageid).name, \
                  'CloseDate':data.expiration_time.isoformat(), \
                  'Expiration_Date__c':data.expiration_time.isoformat(), \
                  'Tableau_App_License_Type__c':data.type, \
                  'Tableau_App_License_Count__c':data.n, \
                  'System_ID__c':data.system_id, \
                  'Hosting_Type__c':data.hosting_type, \
                  'AWS_Region__c':data.aws_zone, \
                  'Palette_Cloud_subdomain__c':data.subdomain \
                 })


import logging

from stage import Stage
from system import System
from utils import to_localtime
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

logger = logging.getLogger('licensing')

SALESFORCE_URL = 'https://na4.salesforce.com'

class SalesforceAPI(object):
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """

    @classmethod
    def _get_connection(cls):
        try:
            username = System.get_by_key('SALESFORCE-USERNAME')
            password = System.get_by_key('SALESFORCE-PASSWORD')
            security_token = System.get_by_key('SALESFORCE-TOKEN')
            salesforce = Salesforce(
                username=username,
                password=password,
                security_token=security_token)
            return salesforce
        except SalesforceAuthenticationFailed:
            logger.error('Error Logging into Salesforce %s %s %s',
                        username, password, security_token)
            return None

    @classmethod
    def get_url(cls):
        return SALESFORCE_URL

    @classmethod
    def lookup_account(cls, data):
        """ Lookup an account and return the id
        """
        conn = cls. _get_connection()
        sql = "SELECT Name, id FROM Account where Name='{0}'"
        account = conn.query(sql.format(data.organization))
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
            conn = cls._get_connection()
            account = conn.Account.create({'Name':data.organization,
                                         'Website':data.website,
                                         'Phone':data.phone})
            accountid = account['id']
            logger.info('Creating Account Name %s Id %s',
                        data.organization, accountid)
        return accountid

    @classmethod
    def update_account(cls, data):
        """ Update an account
        """
        accountid = cls.lookup_account(data)
        if accountid is None:
            conn = cls._get_connection()
            conn.Account.update(accountid,
                               {'Name':data.organization,
                                'Website':data.website,
                                'Phone':data.phone})
            logger.info('Updating Account Name %s Id %s',
                        data.organization, accountid)

    @classmethod
    def delete_account(cls, data):
        """ Delete an account
        """
        accountid = cls.lookup_account(data)
        if accountid is not None:
            conn = cls._get_connection()
            conn.Account.delete(accountid)
            logger.info('Deleted Account Name %s Id %s',
                        data.organization, accountid)

    @classmethod
    def lookup_contact(cls, data):
        """ Lookup a contact
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id " +\
              "FROM Contact where Firstname='{0}' and Lastname='{1}'"
        contact = conn.query(sql.format(data.firstname, data.lastname))
        if contact is None or contact['totalSize'] == 0:
            contactid = None
        else:
            contactid = contact['records'][0]['Id']
        return contactid

    @classmethod
    def lookup_or_create_contact(cls, data, accountid):
        """ Lookup or create contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is None:
            conn = cls._get_connection()
            contact = conn.Contact.create(
                                      {'Firstname':data.firstname,
                                       'Lastname':data.lastname,
                                       'Email':data.email,
                                       'Phone':data.phone,
                                       'AccountId':accountid,
                                       'Admin_Role__c':data.admin_role})
            contactid = contact['id']
            logger.info('Creating Contact Name %s %s Id %s',
                        data.firstname, data.lastname, contactid)

        return contactid

    @classmethod
    def update_contact(cls, data):
        """ Update Contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is not None:
            conn = cls._get_connection()
            conn.Contact.update(contactid,
                                      {'Firstname':data.firstname,
                                       'Lastname':data.lastname,
                                       'Email':data.email,
                                       'Phone':data.phone,
                                       'Admin_Role__c':data.admin_role})
            logger.info('Updating Contact Name %s %s Id %s',
                        data.firstname, data.lastname, contactid)

    @classmethod
    def delete_contact(cls, data):
        """ Deletes a contact
        """
        contactid = cls.lookup_contact(data)
        if contactid is not None:
            conn = cls._get_connection()
            conn.Contact.delete(contactid)
            logger.info('Deleted Contact Name %s %s Id %s',
                        data.firstname, data.lastname, contactid)

    @classmethod
    def get_opportunity_name(cls, data):
        """ Returns the standard name for an opportunity
        """
        name = data.organization + ' ' + \
               data.firstname + ' ' + data.lastname + ' ' +\
               to_localtime(data.registration_start_time).strftime('%x %X')
        return name

    @classmethod
    def new_opportunity(cls, data):
        """ Create a new Salesforce Opportunity
        """
        accountid = cls.lookup_or_create_account(data)
        contactid = cls.lookup_or_create_contact(data, accountid)

        name = cls.get_opportunity_name(data)

        conn = cls._get_connection()
        opp = conn.Opportunity.create(
                {'Name':name, 'AccountId':accountid,
                 'StageName': Stage.get_by_id(data.stageid).name,
                 'CloseDate': data.expiration_time.isoformat(),
                 'Expiration_Date__c': data.expiration_time.isoformat(),
                 'Palette_License_Key__c': data.key,
                 'Palette_Server_Time_Zone__c': data.timezone,
                 'Hosting_Type__c':data.hosting_type,
                 'AWS_Region__c':data.aws_zone,
                 'Palette_Cloud_subdomain__c':data.subdomain,
                 'Promo_Code__c':data.promo_code,
                 'Trial_Request_Date_Time__c':\
                                 data.registration_start_time.isoformat(),
                 'Access_Key__c':data.access_key,
                 'Secret_Access_Key__c':data.secret_key})
        logger.info('Creating new opportunity with Contact ' + \
                    'Name %s %s Account Id %s Contact Id %s',
                    data.firstname, data.lastname, accountid, contactid)
        return opp['id']

    @classmethod
    def update_opportunity(cls, data):
        """ Update a Salesforce Opportunity
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id FROM Opportunity " +\
              "WHERE Palette_License_Key__c='{0}'"
        opp = conn.query(sql.format(data.key))
        if opp is not None and opp['totalSize'] == 1:
            logger.info('Updating opportunity Key %s Stage %s',
                        data.key, Stage.get_by_id(data.stageid).name)

            oppid = opp['records'][0]['Id']
            conn.Opportunity.update(oppid,
                {'StageName':Stage.get_by_id(data.stageid).name,
                 'CloseDate':data.expiration_time.isoformat(),
                 'Expiration_Date__c':data.expiration_time.isoformat(),
                 'Tableau_App_License_Type__c':data.type,
                 'Tableau_App_License_Count__c':data.n,
                 'System_ID__c':data.system_id,
                 'Hosting_Type__c':data.hosting_type,
                 'AWS_Region__c':data.aws_zone,
                 'Palette_Cloud_subdomain__c':data.subdomain,
                 'Promo_Code__c':data.promo_code,
            'Trial_Request_Date_Time__c':data.registration_start_time,
            'Trial_Registered_Date_Time__c':data.trial_start_time.isoformat(),
            'License_Start_Date_Time__c':data.license_start_time.isoformat()
             })

    @classmethod
    def delete_opportunity(cls, data):
        """ Delete an opportunity
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id FROM Opportunity " +\
              "WHERE Palette_License_Key__c='{0}'"
        opp = conn.query(sql.format(data.key))
        if opp is not None and opp['totalSize'] == 1:
            logger.info('Deleting opportunity Key %s Stage %s',
                        data.key, Stage.get_by_id(data.stageid).name)

            oppid = opp['records'][0]['Id']
            conn.Opportunity.delete(oppid)


import logging

from stage import Stage
from system import System
from utils import to_localtime
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

from product import Product

logger = logging.getLogger('licensing')

class SalesforceAPI(object):
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """
    # FIXME:
    # pylint: disable=too-many-public-methods

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
        except SalesforceAuthenticationFailed as ex:
            logger.error('Error Logging into Salesforce %s %s %s: %s',
                        username, password, security_token, str(ex))
            return None

    @classmethod
    def connect(cls):
        username = System.get_by_key('SALESFORCE-USERNAME')
        password = System.get_by_key('SALESFORCE-PASSWORD')
        security_token = System.get_by_key('SALESFORCE-TOKEN')
        sf = Salesforce(username=username,
                        password=password,
                        security_token=security_token)
        return sf

    @classmethod
    def get_url(cls):
        return System.get_by_key('SALESFORCE-URL')

    @classmethod
    def lookup_account(cls, data):
        """ Lookup an account and return the id
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id, Website FROM Account where Website='{0}'"
        account = conn.query(sql.format(data.website))
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
    def get_contact_id(cls, conn, email):
        """Retrieve a contact id by Email address."""
        sql = "SELECT Name, id FROM Contact where Email='{0}'"
        contact = conn.query(sql.format(email))
        if contact is None or contact['totalSize'] == 0:
            contactid = None
        elif contact['totalSize'] != 1:
            raise ValueError("Duplicate contact for email '" + email +"'")
        else:
            contactid = contact['records'][0]['Id']
        return contactid

    @classmethod
    def get_contact_by_email(cls, conn, email):
        """Retrieve a full contact record by Email."""
        contactid = cls.get_contact_id(conn, email)
        if not contactid:
            return None
        return conn.Contact.get(contactid)

    @classmethod
    def get_lead(cls, conn, email):
        """Retrieve a contact by Email address."""
        sql = "SELECT Name, id FROM Lead where Email='{0}'"
        lead = conn.query(sql.format(email))
        if lead is None or lead['totalSize'] == 0:
            leadid = None
        if lead['totalSize'] != 1:
            raise ValueError("Duplicate lead for email '" + email +"'")
        else:
            leadid = lead['records'][0]['Id']
        return leadid

    @classmethod
    def create_contact(cls, conn, email, accountid,
                       fname=None, lname=None, phone=None, admin_role=None):
        #pylint: disable=too-many-arguments
        data = {'Firstname':fname,
                'Lastname':lname,
                'Email':email,
                'Phone':phone,
                'AccountId':accountid,
                'Admin_Role__c':admin_role}
        contact = conn.Contact.create(data)
        logger.info('Created Contact Name %s %s (%s) Id %s',
                    fname, lname, email, contact['id'])
        return contact

    @classmethod
    def lookup_or_create_contact(cls, data, accountid):
        """ Lookup or create contact
        """
        fields = None
        contactid = cls.lookup_contact(data)
        if contactid is None:
            # if contact doesnt exist try leads
            lead = cls.lookup_lead(data)
            if lead is not None:
                # if a lead exists create a contact with the lead info
                fields = {'Firstname':lead['FirstName'],
                          'Lastname':lead['LastName'],
                          'Email':lead['Email'],
                          'Phone':lead['Phone']}
                logger.info('Created contact from lead %s %s %s',
                            data.firstname, data.lastname, lead['Id'])

                # then delete the lead
                cls.delete_lead(lead['Id'])

            if fields is None:
                fields = {'Firstname':data.firstname,
                          'Lastname':data.lastname,
                          'Email':data.email,
                          'Phone':data.phone,
                          'AccountId':accountid,
                          'Admin_Role__c':data.admin_role}

            # create the new contact if it doesnt exist and no lead exists
            accountid = cls.lookup_or_create_account(data)

            conn = cls._get_connection()
            contact = conn.Contact.create(fields)
            contactid = contact['id']

            logger.info('Created Contact Name %s %s Id %s',
                        data.firstname, data.lastname, contactid)
        else:
            logger.info('Contact Id already exists %s', contactid)

        return contactid

    @classmethod
    def upsert_contact(cls, conn, account_id, data):
        """Create or update a contact."""
        if 'Email' not in data:
            raise ValueError("Required field 'Email' not found.")
        email = data['Email']

        data['AccountId'] = account_id

        contact = cls.get_contact_by_email(conn, email)
        if contact:
            conn.Contact.update(contact['Id'], data)
        else:
            contact = conn.Contact.create(data)
        return contact

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
    def lookup_opportunity(cls, key):
        """ Looks up opportunity and returns a dict
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id FROM Opportunity " +\
              "WHERE Palette_License_Key__c='{0}'"
        opp = conn.query(sql.format(key))
        if opp is not None and opp['totalSize'] == 1:
            return opp['records'][0]
        return None

    @classmethod
    def get_opportunity_id(cls, conn, key):
        """ Find an opportunity id by license key"""
        sql = "SELECT Name, id FROM Opportunity " +\
              "WHERE Palette_License_Key__c='{0}'"
        opp = conn.query(sql.format(key))
        if opp is None or opp['totalSize'] == 0:
            oppid = None
        elif opp['totalSize'] != 1:
            raise ValueError("Duplicate opportunities for '" + key + "'")
        else:
            oppid = opp['records'][0]['Id']
        return oppid

    @classmethod
    def get_opportunity_by_key(cls, conn, key):
        """ Retrieve a full opportunity record by license key"""
        oppid = cls.get_opportunity_id(conn, key)
        if oppid is None:
            return None
        return conn.Opportunity.get(oppid)

    @classmethod
    def get_opportunity_name(cls, data):
        """ Looks up opportunity name based on key
        """
        opp = cls.lookup_opportunity(data.key)
        if opp is not None:
            return opp['Name']
        return '*Opportunity not found*'

    @classmethod
    def format_opportunity_name(cls, data):
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

        name = cls.format_opportunity_name(data)

        conn = cls._get_connection()
        row = {'Name':name, 'AccountId':accountid,
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
                 'Secret_Access_Key__c':data.secret_key,
                 'Amount':data.amount}
        if data.productid is not None:
            row['Palette_Plan__c'] = Product.get_by_id(data.productid).name
        opp = conn.Opportunity.create(row)

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
            row = {'Palette_Domain_ID__c':data.id,
                    'StageName':Stage.get_by_id(data.stageid).name,
                    'CloseDate':data.expiration_time.isoformat(),
                    'Expiration_Date__c':data.expiration_time.isoformat(),
                    'Tableau_App_License_Type__c':data.type,
                    'Tableau_App_License_Count__c':data.n,
                    'System_ID__c':data.system_id,
                    'Hosting_Type__c':data.hosting_type,
                    'AWS_Region__c':data.aws_zone,
                    'Access_Key__c':data.access_key,
                    'Secret_Access_Key__c':data.secret_key,
                    'Palette_Cloud_subdomain__c':data.subdomain,
                    'Promo_Code__c':data.promo_code}
            if data.amount is not None:
                row['Amount'] = float(data.amount)
            if data.productid is not None:
                row['Palette_Plan__c'] = data.product.name
            if data.registration_start_time is not None:
                row['Trial_Request_Date_Time__c'] = \
                    data.registration_start_time.isoformat()
            if data.trial_start_time is not None:
                row['Trial_Registered_Date_Time__c'] = \
                   data.trial_start_time.isoformat()
            if data.license_start_time is not None:
                row['License_Start_Date_Time__c'] = \
                   data.license_start_time.isoformat()
            conn.Opportunity.update(oppid, row)

            return oppid
        return None

    @classmethod
    def update_opportunity_details(cls, data, details):
        """ Updates the details that are usually stored in the server
            info table onto Salesforce
        """
        conn = cls._get_connection()
        sql = "SELECT Name, id FROM Opportunity " +\
              "WHERE Palette_License_Key__c='{0}'"
        opp = conn.query(sql.format(data.key))
        if opp is not None and opp['totalSize'] == 1:
            oppid = opp['records'][0]['Id']

            field_map = {'palette-version':'Palette_Version__c',
                         'tableau-version':'Tableau_App_Version__c',
                         'tableau-bitness':'Tableau_App_Bit__c',
                         'processor-type':'Processor_Type__c',
                         'processor-count':'Processor_Count__c',
                         'processor-bitness':'Processor_Bitness__c',
                         'primary-os-version':'Tableau_OS_Version__c'}
            row = {}
            for i in details.keys():
                if i in field_map:
                    row[field_map[i]] = details[i]
            conn.Opportunity.update(oppid, row)

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

    @classmethod
    def lookup_lead(cls, data):
        """ Lookup a lead
        """
        conn = cls._get_connection()
        sql = "SELECT Id, Firstname, Lastname, Email, Company, " + \
              "       Phone, Website " + \
              "FROM Lead where Email='{0}'"
        lead = conn.query(sql.format(data.email))
        if lead is None or lead['totalSize'] == 0:
            result = None
        else:
            result = lead['records'][0]
        return result

    @classmethod
    def delete_lead(cls, leadid):
        """ Delete a lead
        """
        conn = cls._get_connection()
        sql = "SELECT id " + \
              "FROM Lead where id='{0}'".format(leadid)
        lead = conn.query(sql.format(leadid))
        if lead is not None or lead['totalSize'] == 1:
            logger.info('Deleting lead id %s', leadid)
            conn.Lead.delete(leadid)


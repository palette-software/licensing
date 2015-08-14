import logging

from stage import Stage
from system import System
from utils import get_netloc, domain_only
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

from contact import Email
from product import Product

from slack_api import SlackAPI

CONTACT_VERIFIED = 'Verified_Email__c'
CONTACT_EMAIL_BASE = 'Base_Email__c'

logger = logging.getLogger('licensing')

def info(msg, slack=True):
    if slack:
        SlackAPI.info(msg)
    else:
        logger.info(msg)

class SalesforceAPI(object):
    """ Class that uses the salesforce python module to create
        Contcts, Accounts and Opportunities
    """
    # FIXME:
    # pylint: disable=too-many-public-methods

    CONTACT_VERFIED = CONTACT_VERIFIED
    CONTACT_EMAIL_BASE = CONTACT_EMAIL_BASE

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
    def get_account_id(cls, conn, website):
        """ Lookup an account and return the id
        """
        sql = "SELECT Name, id, Website FROM Account where Website='{0}'"
        account = conn.query(sql.format(website))
        if account is None or account['totalSize'] == 0:
            account_id = None
        elif account['totalSize'] != 1:
            raise ValueError("Duplicate account for website '" + website +"'")
        else:
            account_id = account['records'][0]['Id']
        return account_id

    @classmethod
    def get_account_by_website(cls, conn, website):
        """ Retrieve a full account record from the website"""
        account_id = cls.get_account_id(conn, website)
        if account_id is None:
            return None
        return conn.Account.get(account_id)

    @classmethod
    def get_contact_id(cls, conn, email):
        """Retrieve a contact id by Email address."""
        if not isinstance(email, Email):
            email = Email(email)

        sql = "SELECT Name, id FROM Contact where {0}='{1}'"
        contact = conn.query(sql.format(CONTACT_EMAIL_BASE, email.base))
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
    def create_contact(cls, conn, fname, lname, email,
                       verified=True, slack=True):
        """Create a new contact (that definitely doesn't exist) and optionally
        create the associated account.  Returns the contact_id."""
        # pylint: disable=too-many-arguments
        if not isinstance(email, Email):
            email = Email(email)

        # accounts are named by website
        website = get_netloc(domain_only(email.base)).lower()

        account_id = SalesforceAPI.get_account_id(conn, website)
        if account_id is None:
            account = conn.Account.create({'Name': website,
                                           'Website': website})
            account_id = account['id']
            info("*New Account*: '" + website + "'", slack=slack)

        data = {'AccountId': account_id,
                'Firstname': fname,
                'Lastname': lname,
                'Email': email.full,
                CONTACT_EMAIL_BASE: email.base,
                CONTACT_VERIFIED: verified,
        }
        contact = conn.Contact.create(data)

        contact_name = '{0} {1} <{2}>'.format(fname, lname, email.base)
        info("*New Contact* (unverified): '" + contact_name + "'", slack=slack)

        return contact['id'] # NOTE lowercase 'id' on create() response

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
        return contact['id']

    @classmethod
    def contact_roles(cls, conn, opportunity_id):
        """Return all the contact roles for a particular opportunity."""
        soql = "SELECT Id,OpportunityId,ContactId,Role,IsPrimary " +\
               "FROM OpportunityContactRole " +\
               "WHERE OpportunityId = '{0}'"
        roles = conn.query(soql.format(opportunity_id))
        if roles['totalSize'] == 0:
            return None
        return roles['records']

    @classmethod
    def add_contact_role(cls, conn, opportunity_id, contact_id,
                         primary=True, role='Evaluator'):
        """Create a new contact role and return the record id."""
        # pylint: disable=too-many-arguments
        data = {'OpportunityId': opportunity_id,
                'ContactId': contact_id,
                'IsPrimary': primary,
                'Role': role}
        record = conn.OpportunityContactRole.create(data)
        return record['id']

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
    def create_opportunity(cls, conn, name, account_id, entry, slack=True):
        """ Create a new Salesforce Opportunity from a licensing entry.
        Returns the opportunity id.
        """
        # pylint: disable=too-many-arguments
        registration_start_time = entry.registration_start_time.isoformat()

        row = {'Name': name, 'AccountId': account_id,
               'StageName': Stage.get_by_id(entry.stageid).name,
               'CloseDate': entry.expiration_time.isoformat(),
               'Expiration_Date__c': entry.expiration_time.isoformat(),
               'Palette_License_Key__c': entry.key,
               'Hosting_Type__c': entry.hosting_type,
               'AWS_Region__c': entry.aws_zone,
               'Promo_Code__c' :entry.promo_code,
               'Trial_Request_Date_Time__c': registration_start_time,
               'Access_Key__c': entry.access_key,
               'Secret_Access_Key__c': entry.secret_key,
               'Amount':entry.amount} # FIXME: is this valid?
        if not entry.id is None:
            row['Palette_Domain_ID__c'] = entry.id,
        if entry.subdomain:
            row['Palette_Cloud_subdomain__c'] = entry.subdomain,
        if entry.productid is not None:
            row['Palette_Plan__c'] = Product.get_by_id(entry.productid).name
        opp = conn.Opportunity.create(row)
        info("*New Opportunity* " + name, slack=slack)
        return opp['id']

    @classmethod
    def update_opportunity(cls, conn, data):
        """ Update a Salesforce Opportunity"""
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

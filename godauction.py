import os
import logging
import json
import webapp2 as webapp
#import webapp
import jinja2
import pprint

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from operator import itemgetter, attrgetter
from time import strftime

import datetime

now = datetime.datetime.now()

DONATION_TYPE_FOOD = ''
DONATION_TYPE_MONEY = ''
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
YEAR = now.year
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir), 
    extensions=['jinja2.ext.autoescape'], 
    autoescape=True
)

JINJA_ENVIRONMENT.filters['pprint'] = lambda s: pprint.pformat(s)
JINJA_ENVIRONMENT.filters['money'] = lambda x: '$%0.2f' % float(x) if x else '$0.00'
JINJA_ENVIRONMENT.filters['total'] = lambda x: '%0.2f' % float(x) if x else '0.00'
JINJA_ENVIRONMENT.filters['food'] = lambda x: int(x) if x else 0
JINJA_ENVIRONMENT.filters['date'] = lambda s: strftime('%b %-d, %Y', s.timetuple()) if s else 'Never'
JINJA_ENVIRONMENT.filters['time'] = lambda s: strftime('%-I:%M %p', s.timetuple()) if s else 'Never' 
JINJA_ENVIRONMENT.filters['datetime'] = lambda s: strftime('%b %-d, %Y %-I:%M %p', s.timetuple()) if s else 'Never' 

class Power(db.Model):
    added_by = db.UserProperty()
    name = db.StringProperty()
    pantheon = db.StringProperty()
    when_added = db.DateTimeProperty(auto_now_add=True)

class DonationType(db.Model):
    value = db.FloatProperty()
    name = db.StringProperty()

class Donor(db.Model):
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    normalized_name = db.StringProperty()
    normalized_name_reverse = db.StringProperty() # KLUDGE

    def __init__(self, *args, **kwargs):
        first_name = kwargs.pop('first_name', None)
        last_name = kwargs.pop('last_name', None)
        normalized_name = kwargs.pop('normalized_name', None)
        normalized_name_reverse = kwargs.pop('normalized_name_reverse', None)

        if (first_name == None):
            raise Exception("Missing required argument 'first_name'")

        if (last_name == None):
            raise Exception("Missing required argument 'last_name'")

        if (normalized_name == None):
            normalized_name = self.normalize(first_name, last_name)

        if (normalized_name_reverse == None):
            normalized_name_reverse = self.normalize(last_name, first_name)

        db.Model.__init__(self, first_name = first_name, last_name = last_name, normalized_name = normalized_name,
        normalized_name_reverse = normalized_name_reverse)

    def serializable(self):
        """ return a serializable version of this object """
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'normalized_name': self.normalized_name,
        }

    def set_normalized_name_reverse(self):
        self.normalized_name_reverse = self.normalize(self.last_name, self.first_name)

    def set_normalized_name(self):
        self.normalized_name = self.normalize(self.first_name, self.last_name)

    @staticmethod
    def normalize(fname, lname):
        return fname.strip().upper() + lname.strip().upper()

class Donation(db.Model):
    amount = db.FloatProperty()
    donation_type = db.ReferenceProperty(DonationType)
    power = db.ReferenceProperty(Power)
    donor = db.ReferenceProperty(Donor)
    timestamp = db.DateTimeProperty(auto_now_add = True)

class GodAuctionPage(webapp.RequestHandler):
    template_values = {
        'year': YEAR,
        'user': users.get_current_user(),
    }

    def get(self):
        self.template_values['logout_url'] = users.create_logout_url(self.request.uri);

class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()

        logout_url = users.create_logout_url(self.request.uri)

        template_values = {
            'year': YEAR,
            'logout_url': logout_url,
        }

        path = os.path.join('index.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class ListPowers(webapp.RequestHandler):
     def get(self):
        user = users.get_current_user()
        powers_query = Power.all().order('name')
        powers = powers_query.fetch(4)

        logout_url = users.create_logout_url(self.request.uri)

        template_values = {
            'year': YEAR,
            'logout_url': logout_url,
            'powers': powers,
            'user': users.get_current_user(),
            'user_is_admin': users.is_current_user_admin(),
            'scripts': [ os.path.join('powers', 'index.js') ],
        }

        path = os.path.join('powers', 'index.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class AddPower(webapp.RequestHandler):
    def post(self):
        power = Power()

        power.added_by = users.get_current_user()
        power.name = self.request.get('name')
        power.pantheon = self.request.get('pantheon')
        power.put()
        self.redirect('/powers')

    def get(self):
        template_values = {
            'year': YEAR,
            'logout_url': users.create_logout_url(self.request.uri),
        }
        path = os.path.join('powers', 'add.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class ViewPower(webapp.RequestHandler):
    def get(self):
        power_key = self.request.get('power')
        donation_key = self.request.get('donation')
        power = db.get(power_key)
        if donation_key:
            last_donation = db.get(donation_key)

            if last_donation.donation_type.name == "money":
                last_donation.is_money = 1
            else:
                last_donation.is_money = 0
        else:
            last_donation = ''

        donations_query = Donation.all().filter('power =', power)
        food_points = 0
        money_points = 0
        points = {
            'food': 0.0,
            'money': 0.0,
            'total': 0.0,
        }

        by_donor = { }
        for donation in donations_query.run():
            if donation.donation_type:
                multiplier = donation.donation_type.value
                amount = donation.amount * multiplier
                points[donation.donation_type.name] += amount
                points['total'] += amount

                donor_name = ' '.join((donation.donor.first_name, donation.donor.last_name))
                if donor_name not in by_donor:
                    by_donor[donor_name] = {
                        'food': 0,
                        'money': 0,
                        'total': 0,
                    }
                by_donor[donor_name][donation.donation_type.name] += amount
                by_donor[donor_name]['total'] += amount
                if 'name' not in by_donor:
                    by_donor[donor_name]['name'] = donor_name

        donor_totals = {
            'total': sorted(by_donor.items(), key=lambda item: item[1]['total'], reverse=True),
            'food': sorted(by_donor.items(), key=lambda item: item[1]['food'], reverse=True),
            'money': sorted(by_donor.items(), key=lambda item: item[1]['money'], reverse=True),
        }

        template_values = {
            'year': YEAR,
            'power': power,
            'points': points,
            'last_donation': last_donation,
            'donor_totals': donor_totals,
            'logout_url': users.create_logout_url(self.request.uri),
            'scripts': [ os.path.join('powers', 'view.js') ],
            'user_is_admin': users.is_current_user_admin(),
#            'css': [ 'jquery.autocomplete.css' ],
        }

        path = os.path.join('powers', 'view.html')
        template = JINJA_ENVIRONMENT.get_template(path)
        self.response.out.write(template.render(template_values))

class RecordDonation(webapp.RequestHandler):
    def post(self):
        donation = Donation()
        donation.donation_type = DonationType.get_by_key_name(self.request.get('donation_type'))
        donation.power = db.get(self.request.get('power_key'))
        donation.amount = float(self.request.get('amount'))

        donor_name = self.request.get('donor_name').strip()
        if (donor_name.find(' ') != -1):
            (first_name, last_name) = self.request.get('donor_name').split(None, 1)
        else:
            first_name = donor_name
            last_name = ''

        normalized = Donor.normalize(first_name, last_name);
        donor_query = Donor.all().filter("normalized_name =", normalized)
        donor_key = donor_query.get(keys_only=True)
        if not donor_key:
            donor = Donor(first_name = first_name, last_name = last_name, normalized = normalized)
            donor_key = donor.put()
            logging.info('created new donor')
        else:
            logging.info('using existing donor: ')

        donation.donor = donor_key
        donation_key = donation.put()
        self.redirect('/powers/view?power=' + donation.power.key().__str__() + '&donation=' + donation_key.__str__())

class ViewDonor(webapp.RequestHandler):
    def get(self):
        donor_key = self.request.get('donor')
        donor = db.get(donor_key)
        if not donor:
            path = os.path.join('donors', 'none_found.html')
            self.out.response.out.write(template.render(path))
            return
        
	donation_query = Donation.all().filter('donor =', donor)
        donations = donation_query.fetch(donation_query.count())

        template_values = {
            'year': YEAR,
            'donor': donor,
            'donations': donations,
            'user': users.get_current_user(),
            'user_is_admin': users.is_current_user_admin(),
        }
        path = os.path.join('donors', 'view.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class DonorAutocomplete(webapp.RequestHandler):
    def get(self):
        donor_query = Donor.all().order('first_name')
        donors = []
        for donor in donor_query.run():
            donors.append(donor.first_name + ' ' + donor.last_name)

        self.response.out.write("\n".join(donors))

class ListDonors(webapp.RequestHandler):
    def get(self):
        donor_query = Donor.all().order('first_name')
        donors = donor_query.fetch(donor_query.count())
        for donor in donors:
            logging.error('found donor ' + donor.normalized_name + ' ' + donor.first_name + ' ' + donor.last_name);

        template_values = {
            'year': YEAR,
            'donors': donors,
            'logout_url': users.create_logout_url(self.request.uri),
            'user': users.get_current_user(),
            'user_is_admin': users.is_current_user_admin(),
            'scripts': [ os.path.join('donors', 'index.js') ],
        }

        path = os.path.join('donors', 'index.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class ListDonations(webapp.RequestHandler):
    def get(self):
        donation_query = Donation.all().order('-timestamp')

        donations = []
        for donation in donation_query.run():
            donation.total = donation.amount * donation.donation_type.value
            donations.append(donation)

        template_values = {
            'year': YEAR,
            'donations': donations,
            'user': users.get_current_user(),
            'user_is_admin': users.is_current_user_admin(),
            'logout_url': users.create_logout_url(self.request.uri),
            'scripts': [ os.path.join('donations', 'index.js') ],
        }
        path = os.path.join('donations', 'index.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class ListDonationTypes(webapp.RequestHandler):
    def get(self):
        donation_type_query = DonationType.all()
        donation_types = donation_type_query.fetch(donation_type_query.count())

        template_values = {
            'year': YEAR,
            'donation_types': donation_types,
            'logout_url': users.create_logout_url(self.request.uri),
        }
        path = os.path.join('donation_types', 'index.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class RemoveDonor(webapp.RequestHandler):
    def get(self):
        normalized_name = self.request.get('normalized_name')
        donor = None
        if normalized_name:
            user = users.get_current_user()
            if not users.is_current_user_admin():
                path = os.path.join('common', 'denied.html')
            else:
                donor_query = Donor.all().filter("normalized_name =", normalized_name)
                donor_key = donor_query.get(keys_only=True)
                donor = db.get(donor_key)
                for donation in Donation.all(keys_only=True).filter('donor =', donor_key).run():
                    logging.info('deleting donation')
                    db.delete(donation)

                db.delete(donor_key)
                path = os.path.join('donors', 'deleted.html')
        else:
            path = os.path.join('donors', 'none_found.html')

        template_values = {
            'year': YEAR,
            'user': user,
            'action': 'Remove Donor',
            'donor': donor,
            'logout_url': users.create_logout_url(self.request.uri),
        }
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class RemovePower(webapp.RequestHandler):
    def get(self):
        key = self.request.get('key')
        power = None
        if key:
            user = users.get_current_user()
            if not users.is_current_user_admin():
                path = os.path.join('common', 'denied.html')
            else:
                power = db.get(key)
                for donation in Donation.all().filter('power =', power).run():
                    db.delete(donation.key())

                db.delete(key)
                path = os.path.join('powers', 'deleted.html')
        else:
            path = os.path.join('powers', 'none_found.html')

        template_values = {
            'year': YEAR,
            'user': user,
            'action': 'Remove Power',
            'power': power,
            'logout_url': users.create_logout_url(self.request.uri),
        }
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class RemoveDonation(webapp.RequestHandler):
    def get(self):
        key = self.request.get('key')
        donation = None
        if key:
            user = users.get_current_user()
            if not users.is_current_user_admin():
                path = os.path.join('common', 'denied.html')
            else:
                donation = db.get(key)
                donation.total = donation.amount * donation.donation_type.value
                db.delete(key)
                path = os.path.join('donations', 'deleted.html')
        else:
            path = os.path.join('donations', 'none_found.html')

        template_values = {
            'year': YEAR,
            'user': user,
            'action': 'Remove Donation',
            'donation': donation,
            'logout_url': users.create_logout_url(self.request.uri),
        }
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class ViewStandings(webapp.RequestHandler):
    def get(self):
        power_query = Power.all()

        all_donors = {}
        totals = []
        for power in power_query.run():
            total_for = {
                'name': power.name,
                'total_food': 0,
                'total_money': 0,
                'total': 0,
                'money_donor': {
                    'amount': 0,
                },
                'food_donor': {
                    'amount': 0,
                },
            }

            # donations to this power by donor
            by_donor = { }
            for donation in Donation.all().filter('power =', power).run():
                # sum total donations to this power
                amount = donation.amount * donation.donation_type.value
                key = 'total_' + donation.donation_type.name
                total_for[key] += amount
                total_for['total'] += amount

                # sum total donations to this power by donor
                donor_name = ' '.join((donation.donor.first_name, donation.donor.last_name))
                if donor_name not in by_donor:
                    by_donor[donor_name] = {
                        'food': 0,
                        'money': 0,
                        'total': 0,
                    }
                by_donor[donor_name][donation.donation_type.name] += amount
                by_donor[donor_name]['total'] += amount
                if 'name' not in by_donor:
                    by_donor[donor_name]['name'] = donor_name
                    ## end if
                ## end for

            # build up a list of total donations for all donors
            for donor_name in by_donor.keys():
                if donor_name not in all_donors:
                    all_donors[donor_name] = by_donor[donor_name]
                else:
                    for key in by_donor[donor_name]:
                        if key != 'name':
                            all_donors[donor_name][key] += by_donor[donor_name][key]

            total_for['by_donor'] = {
                'total': sorted(by_donor.items(), key=lambda item: item[1]['total'], reverse=True),
                'food': sorted(by_donor.items(), key=lambda item: item[1]['food'], reverse=True),
                'money': sorted(by_donor.items(), key=lambda item: item[1]['money'], reverse=True),
            }

            totals.append(total_for)

        template_values = {
            'totals': sorted(totals, key=itemgetter('total'), reverse=True),
            'year': YEAR,
            'logout_url': users.create_logout_url(self.request.uri),
            'total_points': sorted(all_donors.items(), key=lambda item: item[1]['total'], reverse=True),
            'total_food': sorted(all_donors.items(), key=lambda item: item[1]['food'], reverse=True),
            'total_money': sorted(all_donors.items(), key=lambda item: item[1]['money'], reverse=True),
        }
        path = os.path.join('standings.html')
        template = JINJA_ENVIRONMENT.get_template(path);
        self.response.out.write(template.render(template_values))

class DonorExists(webapp.RequestHandler):
    def get(self):
        first_name = ''
        last_name = ''

        name = self.request.get('name').strip()
        if (name.find(' ') != -1):
            (first_name, last_name) = self.request.get('name').split(None, 1)
        else:
            first_name = name
            last_name = ''

        normalized_name = Donor.normalize(first_name, last_name)
        donor_query = Donor.all().filter("normalized_name =", normalized_name)
        donor = donor_query.get()

        if donor:
            donor = donor.serializable()

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(donor))

class DonorList(webapp.RequestHandler):
    def get(self):
        donor_query = None
        donors = []

        term = self.request.get('term').strip()

        # This merits more than a little explanation.  GAE does not support case insensitive queries.  Nor does it support 'OR'
        # queries.  So to search on first name or last name (which is the point of the 'term' argument) requires a normalized 
        # version of both first name and last name.  Since I am already providing a normalized version of a complete donor name by
        # concatenating first and last names then uppercasing the concatenated string, searching against that normalized name will
        # serve when we are searching for the first name.  When we are searching for the last name, however, we must have a
        # normalized name that begins with the last name.  This is the purpose of the 'normalized_name_reverse' property of Donor.
        # Finally, the reason for two queries here is that we wish to provide an OR operation, thus both queries must be executed.
        # -- 4 Jul 2010 KP
        if term:
            term = term.upper()
            logging.info('got a term: ' + term);

            gql = 'SELECT * FROM Donor WHERE normalized_name >= :1 AND normalized_name < :2'
            donor_query = db.GqlQuery(gql, term, term + u"\ufffd")
            for donor in donor_query:
                donors.append(donor.first_name + ' ' + donor.last_name)

            gql = 'SELECT * FROM Donor WHERE normalized_name_reverse >= :1 AND normalized_name_reverse < :2'
            donor_query = db.GqlQuery(gql, term, term + u"\ufffd")
            for donor in donor_query:
                donors.append(donor.first_name + ' ' + donor.last_name)

        else:
            logging.info('did not got a term')
            donor_query = Donor.all().order('first_name')
            iterable = donor_query.run()
            for donor in iterable:
                logging.info('found donor ' + donor.first_name + ' ' + donor.last_name)
                donors.append(donor.first_name + ' ' + donor.last_name)

        logging.info('here')
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(donors))

application = webapp.WSGIApplication(
     [
        ('/', MainPage),
        ('/powers', ListPowers),
        ('/powers/add', AddPower),
        ('/donation/add', RecordDonation),
        ('/powers/view', ViewPower),
        ('/powers/remove', RemovePower),
        ('/donors/view', ViewDonor),
        ('/donors', ListDonors),
        ('/donors/remove', RemoveDonor),
        ('/donations', ListDonations),
        ('/donations/remove', RemoveDonation),
        ('/donationtypes', ListDonationTypes),
        ('/standings', ViewStandings),
        ('/donor/exists', DonorExists),
        ('/donors/list', DonorList),
     ],
     debug=True
)

def main():
    run_wsgi_app(application)
    global DONATION_TYPE_FOOD
    global DONATION_TYPE_MONEY

    DONATION_TYPE_FOOD = DonationType(name = "food", key_name="food", value = 1.0)
    DONATION_TYPE_MONEY = DonationType(name = "money", key_name="money", value = 1.0)
    DONATION_TYPE_FOOD.put()
    DONATION_TYPE_MONEY.put()

if __name__ == "__main__":
    main()

import stripe

from product import Product
from system import System

class Plan(object):
    """
    A plan is a product plus a price for that product which may differ
    according to customer (determined in Stripe).
    """

    def __init__(self, name=None, quantity=1, price=0):
        self.name = name
        self.quantity = quantity
        self.price = price
        self.amount = price * quantity

    @classmethod
    def get_from_license(cls, entry):
        plan = Plan()

        if entry.plan:
            plan.name = entry.plan

        if entry.productid == Product.get_by_key('PALETTE-PRO').id:
            # return palette pro cost which has a fixed cost
            if not plan.name:
                plan.name = System.get_by_key('PALETTE-PRO-PLAN')
            plan.quantity = 1
        elif entry.productid == Product.get_by_key('PALETTE-ENT').id:
            # return palette enterprise cost which depends on license type
            if entry.type == 'Named-user':
                if not plan.name:
                    plan.name = System.get_by_key('PALETTE-ENT-NAMED-USER-PLAN')
            elif entry.type == 'Core':
                if not plan.name:
                    plan.name = System.get_by_key('PALETTE-ENT-CORE-PLAN')
            plan.quantity = entry.n

        stripe_plan = stripe.Plan.retrieve(plan.name)
        if not stripe_plan:
            raise ValueError("Invalid plan name : '" + plan.name + "'")

        plan.price = stripe_plan.amount / 100
        plan.amount = plan.price * plan.quantity
        return plan


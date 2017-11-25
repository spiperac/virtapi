import yaml
import os.path
from virtapi.settings import SETTINGS

class Plans(object):
    
    def __init__(self):
        
        #loading plans
        self.plans = None
        self.load_plans()

    def load_plans(self):
        '''
        Loads plans from configuration plans file.
        '''
        with open(SETTINGS['PLANSFILE'], 'r') as stream:
            try:
                self.plans = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def save_plans(self):
        '''
        Save plans in configuration plans file.
        '''
        with open(SETTINGS['PLANSFILE'], 'w') as stream:
            try:
                self.plans = yaml.dump(self.plans, stream)
            except yaml.YAMLError as exc:
                print(exc)
 
    def get_plans(self):
        return self.plans

    def get_plan_by_name(self, name):
        for plan in self.plans:
            if plan['name'] == name:
                return plan

    def add_plan(self, plan):
        self.plans.append(plan)
        self.save_plans()

    def delete_plan(self, name):
        if self.exists(name):
            self.plans.remove(self.get_plan_by_name(name))
            self.save_plans()

    def exists(self, name):
        exists = False
        for plan in self.plans:
            if plan['name'] == name:
                exists = True
        return exists


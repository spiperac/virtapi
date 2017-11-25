import yaml
import os.path
from virtapi.settings import SETTINGS
from virtapi.utilities import download

class Templates(object):

    def __init__(self):
        # loading templates
        self.templates = None
        self.load_templates()

        #loading operating systems
        self.operating_systems = []
        self.load_operating_systems()

    def load_templates(self):
        '''
        Loads templates from configuration templates file.
        '''
        with open(SETTINGS['TEMPLATESFILE'], 'r') as stream:
            try:
                self.templates = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
    
    def save_templates(self):
        '''
        Save templates from templates object.
        '''
        with open(SETTINGS['TEMPLATESFILE'], 'w') as stream:
            try:
                yaml.dump(self.templates, stream)
            except yaml.YAMLError as exc:
                print(exc)
    
    def add_template(self, template):
        self.templates.append(template)
        self.save_templates()

    def delete_template(self, template):
        if self.exists(template):
            self.templates.remove(self.get_template_by_name(template))
            self.save_templates()

    def get_templates(self):
        return self.templates

    def load_operating_systems(self):
        '''
        Loading operating systems from templates.
        '''
        if self.templates == None:
            pass
        else:
            for template in self.templates:
                self.operating_systems.append(str(template['os']))

    def get_os_list(self):
        '''
        Returns just loaded list of operating systems.
        '''
        return self.operating_systems

    def get_os_versions(self, os):
        '''
        Returns a list of versions for operating system.
        '''
        versions = []
        for template in self.templates:
            if template['os'] == os:
                versions.append(template['version'])
        return versions

    def get_iso_link(self, os, version):
        '''
        Returns iso path for selected os and version.
        '''
        iso_link = None
        for template in self.templates:
            if template['os'] == os and str(template['version']) == str(version):
                iso_link = template['iso']
        return iso_link

    def get_template_by_name(self, name):
        for template in self.templates:
            if template['name'] == name:
                return template

    def fetch_template(self, os, version):
        '''
        Checks if template exist and if not, download and save it in the standard templates path.
        '''
        link = self.get_iso_link(os, version)
        save_path = SETTINGS['TEMPLATESPATH']
        
        if self.check_exists(link):
            print("Template already exists.")
            return os.path.basename(link)

        try:
            filename = download(link, save_path)
            return filename

        except Exception as e:
            print("Download of the template failed.")
            raise(e)
    
    def exists(self, name):
        exists = False
        for template in self.templates:
            if template['name'] == name:
                exists = True
        return exists

    def check_exists(self, template_iso):
        '''
        Check if template exists.
        '''
        template_file = "{}/{}".format(SETTINGS['TEMPLATESPATH'], os.path.basename(template_iso))
        exists = os.path.exists(template_file)
        return exists

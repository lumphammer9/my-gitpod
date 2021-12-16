"""A general set of keywords to be used for robot testing of
   the 468 platform, starting with the core service's python APIs.

   By convention, anything in Title case is intended primarily as a
   Robot keyword, snake_case is a python method for other libraries.
"""

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
import traceback, os, sys, re
import requests
from ruamel.yaml import YAML

sys.path.append('.')
sys.path.append('./robot_tests')

import robot_settings as settings



import logging as django_logging #Python logging is used by django
import logging_tree



DJANGO_LOG_PATH = 'robot_logs/django_client.logs'

#This is...messy...  We need the builtin library to get a reference to the right
#instance of  Base library, so we create an instance of it here even though
#builtin is supposed to be a globally-scoped library.
BUILTIN = BuiltIn()

class RemoteClient():
  """A client class whose calling signatures match DRF's APIClient class but that
     uses the python requests library to run the tests without running the full backend-services
     django process
  """
  
  def __init__(self, hdp, username, password):
    """
      Arguments:
        hdp (string): A host/domain/port for use in a url, e.g. 'localhost:8000' or 'backend-services.dev.project-468.com'
        username (string): Valid username to auth to the backend as the test user
        password (string): Valid password for the test user
    """
    self.base_url = f'https://{hdp}'
    self.session = requests.Session()
    self.session.headers.update({'Accept': 'application/json'})
    token_path = f'/api/v2/token/'
    rsp = self.session.post(self.base_url + token_path, data = {'username':username, 'password':password})
    if not rsp.status_code == 200:
      raise AssertionError(f"Authenticating to {token_path} with username {username} did not result in http 200, but got: {rsp}\n{rsp.content}")
    self.session.headers.update({'Authorization': f'Bearer {rsp.json()["access"]}', 'Content-Type':'application/json'})
    
  def _check(self, path, data):
    """Check that path and data are valid, raise ValueErrors if not"""
    if not path.startswith('/'):
      raise ValueError(f'path should start with a slash, got {path}')
    if data != None and not isinstance(data, dict):
      raise ValueError(f'expecting dict for data arg')
    pass

  def get(self, path, data=None, expect_status_codes=[200,201]):
    self._check(path, data)
    rsp = self.session.get(self.base_url + path, params=data)
    if expect_status_codes and rsp.status_code not in expect_status_codes:
      raise AssertionError(f"expected {expect_status_codes} from {path} with {data} but got {rsp.status_code} and {rsp.text}")
    return rsp

  def post(self, path, data={}, expect_status_codes=[200,201,204]):
    self._check(path, data)
    rsp = self.session.post(self.base_url + path, json=data)
    if expect_status_codes and rsp.status_code not in expect_status_codes:
      raise AssertionError(f"expected {expect_status_codes} from {path} with {data} but got {rsp.status_code} and {rsp.text}")
    return rsp
    
  def patch(self, path, data = {}, expect_status_codes=[200,201,204]):
    self._check(path, data)
    rsp = self.session.patch(self.base_url + path, json=data)
    if expect_status_codes and rsp.status_code not in expect_status_codes:
      raise AssertionError(f"expected {expect_status_codes} from {path} with {data} but got {rsp.status_code} and {rsp.text}")
    return rsp

  def delete(self, path, data=None, expect_status_codes=[200,201,204]):
    self._check(path, data)
    rsp = self.session.delete(self.base_url + path, params=data)
    if expect_status_codes and rsp.status_code not in expect_status_codes:
      raise AssertionError(f"expected {expect_status_codes} from {path} with {data} but got {rsp.status_code} and {rsp.text}")
    return rsp

  def options(self, path, data=None):
    self._check(path, data)
    return self.session.options(self.base_url + path, params=data)
 

def get_default_client():
  """A bit of weirdness to provide a python interface to other keyword libs
      that want access to the default client.  This is intentionally a module-level
      method that tries to find the right instance of Base and return the default client.
  """
  base = BUILTIN.get_library_instance('Base')
  return base.default_client


class Base(object):
  #Required class attributes from Robot Framework
  ROBOT_LISTENER_API_VERSION = 2
  ROBOT_LIBRARY_SCOPE = "GLOBAL"


  def __init__(self):
      self.ROBOT_LIBRARY_LISTENER = self
      self.last_log = None
      self.default_client = RemoteClient(hdp=settings.DEFAULT_BACKEND_HOST, 
                                          username=settings.DEFAULT_TEST_USER, 
                                          password=settings.DEFAULT_TEST_PW)
      self.default_workspace_name = None
      self._import_settings()

  

  def _log_message(self, message):
      self.last_log = message

  def _end_keyword(self, name, attrs):
      if attrs['status'] == 'FAIL':
          print("\n******\n", self.last_log['message'])

  def _import_settings(self):
    """A hackaround to import the settings.py file regardless of how the user
        has their pythonpath set
    """
    try:
      #Try to find the settings.py file, and hope for the best
      mydir = os.path.dirname(os.path.abspath(__file__))
      myparentdir = os.path.dirname(mydir)
      sys.path.append(mydir) #add this dir to python path
      sys.path.append(myparentdir) #add the parent dir to python path  
      sys.path.append('.') #add the cwd to the python path
      import robot_settings as settings #now look for settings
    except ModuleNotFoundError as me:
      raise AssertionError(f"you must have a robot_settings.py file on your PYTHONPATH" +
                            f"(typically in robot_tests dir), searched {sys.path} and got {me}") from me


  def Hello_World(self):
      print("Hello, World!")

  def Set_Logging_Config(self, **kwargs):
    """A placeholder here for eventually taking arguments to do something
      more useful with log focus.
    """
    dlogger = django_logging.getLogger()
    dlogger.handlers.clear()  #Remove the other handlers
    dlogger.setLevel(django_logging.DEBUG)
    # log  debug messages to file
    fh = django_logging.FileHandler(DJANGO_LOG_PATH)
    fh.setLevel(django_logging.DEBUG)
    fh_formatter = django_logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    dlogger.addHandler(fh)
    # create console handler with a debug log level
    #ch = django_logging.StreamHandler()
    #ch.setLevel(django_logging.DEBUG)
    #ch_formatter = django_logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    #ch.setFormatter(ch_formatter)
    # add the handlers to logger
    #dlogger.addHandler(ch)

    # set the (annoying) django.request handler to Error, otherwise it
    # sends a lot of msgs to stderr when we intentionally try a URL that shouldn't answer
    drh = django_logging.getLogger('django.request')
    drh.setLevel(django_logging.ERROR)

    # set the (chatty) git submodule handler to Info, otherwise it
    # really clouds the logs
    gh = django_logging.getLogger('git')
    gh.setLevel(django_logging.WARNING)

    # set the (chatty) connectionpool submodule handler to Info, otherwise it
    # really clouds the logs
    cph = django_logging.getLogger('connectionpool')
    cph.setLevel(django_logging.INFO)

    # print the actual logging config to the log
    dlogger.debug(logging_tree.format.build_description())

  def Get_Logging_Config(self):
    return logging_tree.format.build_description()

  def Get_Setting(self, name, default=None):
    """Abstract out the settings.py file (or future approach to setting settings).
    """
    if hasattr(settings, name):
      return getattr(settings, name)
    else:
      return default


  def Yo_to_ys(self, yo):
    """Convert a dict-of-dicts-like yaml object like those used
      by K8s to a yaml string.
    """
    sio = io.StringIO()
    YAML().dump(yo, sio)
    return sio.getvalue() 

  def Ys_to_yo(self, ystr):
    """Convert a string (contents of a yaml file)
      to a dict-of-dicts like object used here.
    """
    return YAML().load(ystr)

  def Load_Template(self, file_name, template_dir='../templates', **kwargs):
    """Load a template from the template_dir directory, fill it with the kwargs.

      The template should be python style, i.e. vars in {braces}.
      
      Note that as a hack-around, if this discovers ${...} syntax in a file ending with
      .robot, it assumes those are *not* python template braces.

      Args:
        file_name (str): File to load as the template
        template_dir (str): Absolute or relative path (relative to *this file*) to find templates
    """
    if not os.path.isabs(template_dir):
      thisdir = os.path.dirname(os.path.abspath(__file__))
      template_dir = os.path.join(thisdir, template_dir)
    fpath = os.path.join(template_dir, file_name)
    if not os.path.exists(fpath):
      raise FileNotFoundError(f"No template file found at {fpath}")
    with open(fpath, 'r') as f:
      fc = f.read()
      if file_name.endswith('.robot'): #Hack around to escape robot var
        fc = re.sub(r'\$\{([^}]*)\}', r'${{\1}}', fc)
      try:
        ret = fc.format(**kwargs)
        return ret
      except KeyError as e:
        raise AssertionError(f"key '{e.args[0]}' was not provided for template {fc}") from e


  
  def Load_Template_Or_None(self, file_name, template_dir='../templates', **kwargs):
    """Similar to Load_Template, but returns None rather than throwing error (used to avoid
        conditionals leaking in to Robot)
    """
    try:
      return self.Load_Template(file_name, template_dir)
    except FileNotFoundError:
      return None
  
  def Execute(self, *lines):
    """Execute arbitrary python code (very dangerous).  Raise an exception if you want the test to fail.

      Example:
        (In a foo.robot file):
        Create and Delete A Workspace, Python API
          ${NAME}=                      Set Variable                    test-workspace-1
          ${workspace_repo_url}=        Create Gitservice Repo          ${GITSERVICE_GROUP_NAME}        ${NAME}
          Execute                       from coreapi.models import Workspace
          ...                           workspace = Workspace(workspace_name='${NAME}')
          ...                           workspace.workspace_repo_url='${workspace_repo_url}'
          ...                           workspace.save()
          ...                           workspace2 = Workspace.objects.get(workspace_repo_url='${workspace_repo_url}')
          ...                           if(workspace2 != workspace) raise AssertionError("Test fail")
  
      Note that this implementation is not *that* smart.  It executes the python line by line, so multi-line
      scripts (most frustratingly try/except blocks) won't work.N
    """
    lineno = 0
    globals = {}
    locals = {}
    for line in lines:
      try:
        lineno += 1
        ret = exec(line, globals, locals)
      except Exception as e:
        orig_stacktrace = "\t".join(traceback.TracebackException.from_exception(e).format())
        #print(f"*ERROR* Exception thrown in python, {lineno}: {line}: \nOriginating Stacktrace:\n{orig_stacktrace}")
        raise AssertionError(f"Error in python code, line {lineno}: {line}: {e} ({type(e)})\n\tOriginating Stacktrace:\n{orig_stacktrace}") from e


  def Init_Default_Workspace(self, name, group_name=settings.DEFAULT_WORKSPACE_GIT_GROUP, exist_ok=False):
    """For convenience, creates a workspace and inits it as the default for this suite.
        Returns a python response object for troubleshooting purposes.
    """
    self.default_workspace_name = name
    return self.Create_Workspace(name, group_name, exist_ok)

  def Set_Default_Workspace(self, name):
    """Sets the name of the default workspace assuming it was created
        wihtout Init Default Workspace
    """
    self.default_workspace_name = name
    return self.default_workspace_name
    
  def Get_Default_Workspace(self):
    """Returns the name of the default workspace
    """
    return self.default_workspace_name

  def Create_Workspace(self, name, group_name=settings.DEFAULT_WORKSPACE_GIT_GROUP, exist_ok=False):
    """Creates a new Workspace object via the REST API.  o.
  
      Args:
        name (str): Name to be used in both db and git repo
        group_name (str): Defaults to the default name in django settings.py
        exist_ok (bool): If true, raise exception if this workspace already exists

      Returns:
        Returns a response object (check .status_code, .content, or .json()).
    """
    wjson={'name': name, 'group_name': group_name,}
    rsp = self.default_client.post('/api/v2/workspaces/', wjson)
    if not exist_ok and not rsp.status_code == 201:
      raise AssertionError(f"Creating workspace failed: {rsp.content}")  
    return rsp

  def Delete_Workspace(self, name):
    """Deletes the Workspace via the REST API.  If the workspace doesn't exist,
      just keep on rolling.  Note for test purposes, the preferred approach
      is to use Teardown_Workspace which uses the devkit APIs to do a complete/safer
      teardown of all backend-services and corestate state related to this workspace.
    """
    rsp = self.default_client.delete(f'/api/v2/workspaces/{name}')
    if rsp.status_code == 204: #This is a successful delete
      return rsp
    elif rsp.status_code == 404: #This is a safe 'not found' error
      return rsp
    else:
      raise AssertionError(f"Deleting workspace {workspace_name} failed with a status code {rsp.status_code}:\n{rsp.content}")
    return rsp

  def Teardown_Workspace(self, name):
    """Goes beyond delete to teardown any other resources we can find 
        related to this workspace as a dev-time helper.
    """
    rsp = self.default_client.post(f'/api/v2/teardown', {'workspace':name})
    if not rsp.status_code == 200:
      raise AssertionError(f"Teardown workspace failed: {rsp.status_code}: {rsp.text}")
    logger.debug(f"Tearing down workspace {name}: {rsp.text}")
    return rsp

  # def Create_Draft_Slx(self, slx_name, workspace_name=None, exist_ok=False):
  #   """Creates an Slx in the session branch.  If no workspace name is given, try to use
  #     the one from Get_Default_Workspace
  #   """
  #   if not workspace_name:
  #     workspace_name=self.default_workspace_name

  #   if not workspace_name:
  #     raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

  #   logger.debug(f"creating draft slx for {workspace_name} / {slx_name}")
    
  #   rsp = self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs', {'name':slx_name})
  #   if not exist_ok and not rsp.status_code == 201:
  #     raise AssertionError(f"Creating draft slx failed: {rsp.content} with status code {rsp.status_code}")

  # def Create_Draft_Sli(self, slx_name, workspace_name=None, exist_ok=False):
  #   if not workspace_name:
  #     workspace_name=self.default_workspace_name

  #   if not workspace_name:
  #     raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

  #   logger.debug(f"creating draft sli for {workspace_name} / {slx_name}")

  #   rsp = self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli', {})
  #   if not exist_ok and not rsp.status_code == 201:
  #     raise AssertionError(f"Creating draft sli failed: {rsp.content}")

  # def Create_Draft_Slo(self, slx_name, workspace_name=None, exist_ok=False):
  #   if not workspace_name:
  #     workspace_name=self.default_workspace_name
  #   if not workspace_name:
  #     raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

  #   logger.debug(f"creating draft slo for {workspace_name} / {slx_name}")

  #   rsp = self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/slo', {})
  #   if not exist_ok and not rsp.status_code == 201:
  #     raise AssertionError(f"Creating draft slo failed: {rsp.content}")

  # def Create_Draft_Slx_And_Sli(self, slx_name, workspace_name=None, exist_ok=False):
  #   """Creates both an Slx and an Sli in the session branch.  If workspace_name is none,
  #     use the Defaul_Workspace
  #   """
  #   if not workspace_name:
  #     workspace_name=self.default_workspace_name
  #   if not workspace_name:
  #     raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")


  #   self.Create_Draft_Slx(slx_name, workspace_name, exist_ok)
  #   self.Create_Draft_Sli(slx_name, workspace_name, exist_ok)


  def Merge_Draft_To_Prod(self, workspace_name=None):
    """Merges the session branch to production
    """
    if not workspace_name: 
      workspace_name=self.default_workspace_name
    if not workspace_name:
      raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

    rsp = self.default_client.post(f'/api/v2/workspaces/{workspace_name}/merge_to_prod', {})
    if not rsp.status_code == 201:
      raise AssertionError(f"merge draft to prod failed: {rsp.content}")

  def Create_Draft_Slx(self, slx_name, workspace_name=None,
                                      slx_yaml=None,
                                      slx_config_provided=None,
                                      sli_yaml=None,
                                      sli_locations=None, 
                                      sli_config_provided=None,
                                      sli_robot_contents=None, 
                                      sli_reqs_contents=None, 
                                      slo_yaml=None,
                                      slo_query_contents=None,
                                      rb_yaml=None,
                                      rb_location=None,
                                      rb_robot_contents=None,
                                      rb_reqs_contents=None,
                                      rb_config_provided=None,
                                      hook_yaml=None,
                                      exist_ok=False):
    """Creates a draft SLX with children.  This is intended as an omnibus call with many optional 
       arguments to fit various calling styles.

       With no other arguments, it creates the Slx in the session branch with a default slx.yaml.  If
       any of the sli_* arguments are specified, it creates an Sli in the session branch.  If any slo_*
       arguments are specified, it creates an Slo in the session branch, etc, etc.

       Args:
        slx_name (str): The slx name to use, see exist_ok
        workspace_name (str): The workspace name to use (needs to already exist), or None
                              to use the default workspace
        slx_yaml (str): Contents of the slx.yaml file, or None to use the platform default
        slx_config_provided list[dict[str, Union(str, dict)]]: A list of dicts to use for configProvided
                                                contents of the form
                                                [{'name':'foo', 'value':'bar'}]
        sli_yaml (str): Contents of the sli.yaml file, or None to use the platform default
        sli_locations (Union(str, list[str])): A string or list of strings for prod locations
                                          to deploy this sli 
        sli_robot_contents (str): A string representing the contents of an sli.robot file
        sli_reqs_contents (str): A string representing the contents of a requirements.txt
        sli_config_provided list[dict[str, Union(str, dict)]]: See slx_config_provided for form
        slo_yaml (str): Contents of the slo.yaml file, or None to use the platform default
        slo_query_contents (str): A string representing the contents of the slo's query.yaml file
        rb_yaml (str): Contents of the runbook.yaml file, or None to use the platform default
        rb_location (str): A string for prod locations to deploy this runbook.  Note *single* location,
                           unlike the sli that can take an array of locations
        rb_robot_contents (str): A string representing the contents of an runbook.robot file
        rb_reqs_contents (str): A string representing the contents of a requirements.txt
        rb_config_provided list[dict[str, Union(str, dict)]]: See slx_config_provided for form
        hook_yaml (str): Contents of the hook.yaml file, or None to use the platform default
        exist_ok (boo): Error if the slx already exists
    """
    if not workspace_name:
      workspace_name=self.default_workspace_name

    if not workspace_name:
      raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")
    
    #Create the SLX
    expect_status_codes = [201]
    if exist_ok:
      expect_status_codes.append(422)
    self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs', 
                             {'name':slx_name}, 
                             expect_status_codes=expect_status_codes)

    #SLX yaml (optional)
    if slx_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/config/branches/--', 
                               {'yaml':slx_yaml}, 
                               expect_status_codes=[201])

    #Patch the SLX (optional)
    slx_spec_patch = {}
    if slx_config_provided != None:
      slx_spec_patch = {'configProvided': list(slx_config_provided)}
      self.default_client.patch(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/config/branches/--", 
                                data={'spec': slx_spec_patch})

    #Create an SLI? (optional)
    if sli_yaml or sli_locations or sli_robot_contents or sli_reqs_contents or sli_config_provided:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli', expect_status_codes=[201])

    #Over-ride the default SLI yaml (optional)
    if sli_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli/config/branches/--', 
                               {'yaml':sli_yaml},
                               expect_status_codes=[201])

    #Patch the SLI (optional)
    sli_spec_patch = {}
    if sli_locations != None and len(sli_locations) > 0:
      if isinstance(sli_locations, str):
        sli_locations = [sli_locations]
      sli_spec_patch['locations'] = sli_locations
    if sli_config_provided != None:
      sli_spec_patch['configProvided'] = sli_config_provided
    if len(sli_spec_patch) > 0:
      self.default_client.patch(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli/config/branches/--", data={'spec': sli_spec_patch})

    #Create the SLI codebundle files (optional)
    p = {}
    if sli_robot_contents:
      p['sli.robot'] = sli_robot_contents
    if sli_reqs_contents:
      p['requirements.txt'] = sli_reqs_contents
    if len(p) > 0:
      self.default_client.post(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli/code/branches/--", data=p)

    #Create an SLO?  (optional)
    if slo_yaml or slo_query_contents:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/slo', expect_status_codes=[201])

    #Over-ride the default SLO yaml (optional)
    if slo_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/slo/config/branches/--', 
                               {'yaml':slo_yaml},
                               expect_status_codes=[201])

    #Create the SLO codebundle files (optional)
    p = {}
    if slo_query_contents:
      p['queries.yaml'] = slo_query_contents
      self.default_client.post(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/slo/code/branches/--", data=p)

    #Create a Runbook? (optional)
    if rb_yaml or rb_location or rb_config_provided or rb_robot_contents or rb_reqs_contents:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/runbook', expect_status_codes=[201])

    #Over-ride the default Runbook yaml (optional)
    if rb_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/runbook/config/branches/--', 
                               {'yaml':rb_yaml},
                               expect_status_codes=[201])

    #Patch the Runbook (optional)
    rb_spec_patch = {}
    if rb_location != None:
      rb_spec_patch['location'] = rb_location
    if rb_config_provided != None:
      rb_spec_patch['configProvided'] = rb_config_provided
    if len(rb_spec_patch) > 0:
      self.default_client.patch(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/runbook/config/branches/--", 
                                data={'spec': rb_spec_patch})

    #Create the Runbook codebundle (optional)
    p = {}
    if rb_robot_contents:
      p['runbook.robot'] = rb_robot_contents
    if rb_reqs_contents:
      p['requirements.txt'] = rb_reqs_contents
    if len(p) > 0:
      self.default_client.post(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/runbook/code/branches/--", data=p)

    #Create a Hook? (optional)
    if hook_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/hook', expect_status_codes=[201])

    #Over-ride the default Hook yaml (optional)
    if hook_yaml:
      self.default_client.post(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/hook/config/branches/--', 
                               {'yaml':hook_yaml},
                               expect_status_codes=[201])



  def Create_Prod_Slx(self, slx_name, workspace_name=None,
                                      slx_yaml=None,
                                      slx_config_provided=None,
                                      sli_yaml=None,
                                      sli_locations=None, 
                                      sli_config_provided=None,
                                      sli_robot_contents=None, 
                                      sli_reqs_contents=None, 
                                      slo_yaml=None,
                                      slo_query_contents=None,
                                      rb_yaml=None,
                                      rb_location=None,
                                      rb_robot_contents=None,
                                      rb_reqs_contents=None,
                                      rb_config_provided=None,
                                      hook_yaml=None,
                                      exist_ok=False):
  
    """
    See documentation for Create_Draft_Slx.  This passes through to that function,
    then merges the session branch to production.

    If there were sli arguments passed, this will also block with a wait_for_ready API call
    until the SLI's containers are running in the locations in the spec.
    """
    self.Create_Draft_Slx(slx_name=slx_name, workspace_name=workspace_name,slx_yaml=slx_yaml,
                          slx_config_provided=slx_config_provided, sli_yaml=sli_yaml, sli_locations=sli_locations,
                          sli_config_provided=sli_config_provided, sli_robot_contents=sli_robot_contents,
                          sli_reqs_contents=sli_reqs_contents, slo_yaml=slo_yaml, slo_query_contents=slo_query_contents,
                          rb_yaml=rb_yaml, rb_location=rb_location, rb_robot_contents=rb_robot_contents, 
                          rb_reqs_contents=rb_reqs_contents, rb_config_provided=rb_config_provided, hook_yaml=hook_yaml,
                          exist_ok=exist_ok)

    #Merge to production and wait until it is rolled out to locations
    self.Merge_Draft_To_Prod(workspace_name=workspace_name)

    #If there were slis involved, wait_for_ready
    if sli_yaml or sli_locations or sli_config_provided or sli_robot_contents or sli_reqs_contents:
      self.default_client.get(f"/api/v2/workspaces/{workspace_name}/slxs/{slx_name}/sli/wait_for_ready")


  def Teardown_Slx_And_Reset_Session_Branch(self, slx_name, workspace_name=None):
    if not workspace_name:
      workspace_name=self.default_workspace_name
    if not workspace_name:
      raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

    rsp = self.default_client.delete(f'/api/v2/workspaces/{workspace_name}/slxs/{slx_name}')
    self.Reset_Session_Branch(workspace_name)
    if rsp.status_code not in [204,404]:
      raise AssertionError(f"teardown slx failed: {rsp.status_code}: {rsp.content}")

  def Reset_Session_Branch(self, workspace_name=None):
    if not workspace_name:
      workspace_name=self.default_workspace_name
    if not workspace_name:
      raise AssertionError("The workspace_name must be either set as an argument here or by the Init Default Workspace keyword")

    rsp = self.default_client.delete(f'/api/v2/workspaces/{workspace_name}/branches/--')
    if not rsp.status_code == 204:
      raise AssertionError(f"failed to reset session branch: got {rsp.status_code}: {rsp.text}")
  


  

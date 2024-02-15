import json
import logging
import requests.exceptions

from typing import List
from urllib.parse import urljoin, urlparse, parse_qs
from requests_toolbelt.multipart.encoder import MultipartEncoder

from openedx_rest_api_client.session import OAuthAPISession

logger = logging.getLogger(__name__)
# URLs

URL_LIB_PREFIX = '/api/libraries/v2/'
URL_LIB_CREATE = URL_LIB_PREFIX
URL_LIB_DETAIL = URL_LIB_PREFIX + '{lib_key}/'  # Get data about a library, update or delete library
URL_LIB_BLOCK_TYPES = URL_LIB_DETAIL + 'block_types/'  # Get the list of XBlock types that can be added to this library
URL_LIB_LINKS = URL_LIB_DETAIL + 'links/'  # Get the list of links defined for this content library
URL_LIB_LINK = URL_LIB_DETAIL + 'links/{link_id}/'  # Update a specific link
URL_LIB_COMMIT = URL_LIB_DETAIL + 'commit/'  # Commit (POST) or revert (DELETE) all pending changes to this library
URL_LIB_BLOCKS = URL_LIB_DETAIL + 'blocks/'  # Get the list of XBlocks in this library, or add a new one
URL_LIB_BLOCK = URL_LIB_PREFIX + 'blocks/{block_key}/'  # Get data about a block, or delete it
URL_LIB_BLOCK_OLX = URL_LIB_BLOCK + 'olx/'  # Get or set the OLX of the specified XBlock
URL_LIB_BLOCK_ASSETS = URL_LIB_BLOCK + 'assets/'  # Get the static asset files belonging to the specified XBlock
URL_LIB_BLOCK_ASSET = URL_LIB_BLOCK + 'assets/{filename}'  # Get a static asset file belonging to the specified XBlock

URL_BLOCK_BASE = '/api/xblock/v2/xblocks/{block_key}/'
URL_BLOCK_METADATA = URL_BLOCK_BASE
URL_BLOCK_RENDER_VIEW = URL_BLOCK_BASE + 'view/{view_name}/'
URL_BLOCK_GET_HANDLER_URL = URL_BLOCK_BASE + 'handler_url/{handler_name}/'
BLOCK_GET_HANDLER_URL_CACHE_KEY = '{username}:{url}'

URL_PATHWAYS_PREFIX = '/api/lx-pathways/v1/pathway/'
URL_PATHWAYS_DETAIL = URL_PATHWAYS_PREFIX + '{pathway_key}/'
URL_PATHWAYS_PUBLISH = URL_PATHWAYS_PREFIX + '{pathway_key}/publish/'

URL_MODULESTORE_BLOCK_OLX = '/api/olx-export/v1/xblock/{block_key}/'

URL_COURSES_BASE = '/api/courses/v1/'
URL_COURSES_LIST = URL_COURSES_BASE + 'courses/'
URL_COURSES_BLOCKS = URL_COURSES_BASE + 'blocks/'
COURSE_LIST_CACHE_KEY = 'course-list:{username}:{org}'

URL_ENROLLMENT_BASE = '/api/enrollment/v1/'
URL_ENROLLMENT_ROLES = URL_ENROLLMENT_BASE + 'roles/'

URL_BULKENROLL = '/api/bulk_enroll/v1/bulk_enroll'
URL_VALIDATION_REGISTRATION = '/api/user/v1/validation/registration'
URL_ACCOUNT_REGISTRATION = '/api/user/v1/account/registration/'

URL_COURSE_GRADES = '/api/grades/v1/courses/{course_id}/'


class OpenedxRESTAPIClient:
    """ A client to access Open edX REST API endpoints.

    Usage example::
        client = OpenedxRESTAPIClient(
            base_url='https://lms.example.com',
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
            )
        courses = client.list_all_courses()

    For information about all Open edX endpoint please see
    https://github.com/edx/edx-platform/blob/161e3560dde9edf1c2bacedf2dd442dc077a8cbf/docs/swagger.yaml

    """
    def __init__(self,
                 base_url: str,
                 client_id: str,
                 client_secret: str,
                 timeout: (float, float) = None,
                 bearer: bool = True,
                 **kwargs) -> None:
        """ Opens a session with the LMS

        Args:
            base_url: url of the LMS. Must include the schema (https:// or http://)
            client_id: Client Id. Created in <lms base url>/admin/oauth2/client/
            client_secret: Client secret for the client Id.
            bearer: If True, it will request a bearer token. Otherwise it will request a jwt token.
            **kwargs: are passed to :class:`session.OAuthAPISession`


        """
        self._base_url = base_url
        self.session = OAuthAPISession(base_url, client_id, client_secret,
                                       timeout,
                                       bearer,
                                       **kwargs)

    def _post_form(self, path:str, params:dict, url:str=None) -> requests.Response:
        """
        Sends a post with form encoding.
        Args:
            path: path of the API endpoint.
            params: dict with data to post.
            url: base url. If empty, will take the base url.

        Returns:
            response
        """
        data = MultipartEncoder(fields=params)

        headers = {
            'Content-Type': data.content_type
        }

        endpoint = urljoin(url if url else self._base_url, path)
        response = self.session.post(
            headers=headers,
            url=endpoint,
            data=data,
        )
        if response.status_code != 200:
            logger.error(f"Error {response.status_code} in post form to {endpoint} with params {json.dumps(params)}: "
                         f"{response.text}")

        return response

    def _post_json(self, path: str, params: dict, url: str = None) -> requests.Response:
        """
        Sends a post with json encoding.
        Args:
            path: path of the API endpoint.
            params: dict with data to post.
            url: base url. If empty, will take the base url.

        Returns:
            response
        """
        endpoint = urljoin(url if url else self._base_url, path)
        response = self.session.post(
            url=endpoint,
            json=params,
        )
        if response.status_code != 200:
            logger.error(f"Error {response.status_code} in post json to {endpoint} with params {json.dumps(params)}: "
                         f"{response.text}")

        return response

    def list_all_courses(self,
                         org: str = None,
                         username: str = None,
                         search_term: str = None,
                         **kwargs
                         ) -> List[dict]:
        # pylint: disable=line-too-long
        """
        Get the full list of courses visible to the requesting user.
        Calls the /api/courses/v1/courses LMS endpoint

        Args:
            org: filter by organization
            username: The name of the user the logged-in user would like to be identified as
            search_term: Search term to filter courses (used by ElasticSearch).
                ENABLE_COURSEWARE_SEARCH feature must be enabled in LMS.
            kwargs: If specified, visible `CourseOverview` objects are filtered by the given key-value pairs.
                Not all fields are supported for filtering. See https://github.com/edx/edx-platform/blob/fb8b03178cce836186fc74e17c010cae99738d23/lms/djangoapps/course_api/forms.py#L48

        Returns:
            List of dict in the form:
                [
                   {
                      "blocks_url": "https://lms.example.com/api/courses/v1/blocks/?course_id=course-v1%3A<org>%2B<code>%2B<edition>",
                      "effort":"01:00",
                      "end":"None",
                      "enrollment_start":"None",
                      "enrollment_end":"None",
                      "id":"course-v1:<org>+<code>+<run>",
                      "media":{
                         "course_image":{
                            "uri":"<img path>"
                         },
                         "course_video":{
                            "uri":"None"
                         },
                         "image":{
                            "raw":"<img url>",
                            "small":"<img url>",
                            "large":"<img url>"
                         }
                      },
                      "name":"Course name",
                      "number":"<edition>",
                      "org":"<org>",
                      "short_description":"",
                      "start":"2018-01-11T00:00:00Z",
                      "start_display":"11 de Enero de 2018",
                      "start_type":"timestamp",
                      "pacing":"instructor",
                      "mobile_available":true,
                      "hidden":false,
                      "invitation_only":false,
                      "course_id":"course-v1:<org>+<code>+<edition>"
                   },
                   ...
                ]

        """

        def _get_courses(url, params_=None):
            """ Recursively load all pages of course data. """
            response = self.session.get(urljoin(url, URL_COURSES_LIST), params=params_)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            next_page_url = data.get("pagination", {}).get("next")
            if next_page_url:
                next_page = urlparse(next_page_url)
                results += _get_courses(next_page_url, parse_qs(next_page.query))

            return results

        params = {}
        if org:
            params['org'] = org
        if username:
            params['username'] = username
        if kwargs:
            params['filter_'] = str(kwargs)
        if search_term:
            params['search_term'] = search_term
        course_list = _get_courses(self._base_url, params)

        return course_list

    def change_enrollment(self,
                          emails: List[str],
                          courses: List[str],
                          action: str = 'enroll',
                          url: str = None,
                          auto_enroll: bool = True,
                          email_students: bool = True,
                          cohorts: List[str] = None) -> dict:
        """ Enroll or unenroll (depending on the value of action) the list of emails in the list of courses.
        Calls the /api/bulk_enroll/v1/bulk_enroll/ LMS endpoint

        Args:
            emails: list of emails to enroll
            courses: list of course ids to enroll
            action: can be 'enroll' or 'unenroll'
            url: url of the LMS (base or site). If not specified, uses the base url of the session.
                Defaults to the LMS base.
            auto_enroll: if true, the users will be automatically enrolled as soon as they register.
                Defaults to true.
            email_students: if true, an email will be sent with the update. Defaults to true.
            cohorts: List of cohort names to add the students to.

        Returns:
            dict in the form:
            - If the course does not exist:
            { 'detail': 'Not found' }
            - If successful:
            {
               "action":"enroll",
               "courses":{
                  "course-v1:ORG+CODE+EDITION":{
                     "action":"enroll",
                     "results":[
                        {
                           "identifier":"mail@example.com",
                           "after":{
                              "enrollment":true,
                              "allowed":false,
                              "user":true,
                              "auto_enroll":false
                           },
                           "before":{
                              "enrollment":false,
                              "allowed":false,
                              "user":true,
                              "auto_enroll":false
                           }
                        },
                        ...
                     ],
                     "auto_enroll":true
                  },
                  ...
               },
               "email_students":true,
               "auto_enroll":true
            }
        """

        data = {
            "auto_enroll": auto_enroll,
            "email_students": email_students,
            "action": action,
            "courses": ','.join(courses),
            "identifiers": ','.join(emails)
        }
        if cohorts:
            data['cohorts'] = ','.join(cohorts)

        response = self._post_json(path=URL_BULKENROLL, params=data, url=url)

        if response.status_code == 200:
            return response.json()
        else:
            return {
                'status_code': response.status_code,
                'response': response.text
            }

    def register_account(self,
                         email: str,
                         username: str,
                         name: str,
                         password: str,
                         url: str = None,
                         **kwargs
                         ) -> dict:
        """
        Registers a new user account. Calls the `/api/user/v1/account/registration/` API endpoint.
        View handling the API request: https://github.com/openedx/edx-platform/blob/46bd8fb12fef49d67a0dc531416ed153f3414cfb/openedx/core/djangoapps/user_authn/views/register.py#L520

        Args:
            email: email to register
            username: username to register
            name: full name of the user
            password: password
            url: url of the LMS (base or site). If not specified, uses the base url of the session.
                Defaults to the LMS base.

        Additional default fields accepted:
            name: full name of the user
            level_of_education *: can be:
                'p': 'Doctorate'
                'm': "Master's or professional degree"
                'b': "Bachelor's degree"
                'a': "Associate degree"
                'hs': "Secondary/high school"
                'jhs': "Junior secondary/junior high/middle school"
                'el': "Elementary/primary school"
                'none': "No formal education"
                'other': "Other education"
            gender *: can be 'm', 'f', or 'o'
            mailing_address *
            city *
            country: ISO3166-1 two letters country codes as used in django_countries.countries *
            goals *
            year_of_birth *: numeric 4-digit year of birth
            honor_code *: Bool. If mandatory and not set will not create the account.
            terms_of_service *: Bool. If unset, will be set equally to honor_code
            marketing_emails_opt_in *: Bool. If set, will add a is_marketable user attribute (see Student > User Attributes in Django admin)
            provider: Oauth2 provider information
            social_auth_provider: Oauth2 provider information

            * Can be set as hidden, optional or mandatory in REGISTRATION_EXTRA_FIELDS setting.


        Returns:
            Dict with the form:
            - If successful:
            {
                'success': True,
                'redirect_url': <redirection url to finish the authorization and go to the dashboard>
            }
            - If error:
            {
                <field name>: [
                    {'user_message': <error message>}
                ]
                'error_code': <error code>,
                'username_suggestions': [<username suggestions> * 3]
            }
        """

        params = {
            "email": email,
            "username": username,
            "name": name,
            "password": password,
        }

        params.update(kwargs)

        response = self._post_form(path=URL_ACCOUNT_REGISTRATION, url=url, params=params)

        return response.json()

    def get_course_grades(self, course_id, username=None) -> List[dict]:
        def _get_course_grades(url, _course_id, _params=None):
            """ Recursively load all grades for a course. """
            response = self.session.get(urljoin(url, URL_COURSE_GRADES.format(course_id=_course_id)), params=_params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                results = data.get('results', [])
                if next_page_url := data.get('next'):
                    results += _get_course_grades(next_page_url, _course_id, parse_qs(urlparse(next_page_url).query))
            else:
                results = data
            return results

        params = {}
        if username:
            params['username'] = username

        return _get_course_grades(self._base_url, course_id, params)

    def validation_registration(self, url: str = None, **kwargs) -> dict:
        """
        Validates the account registration form.

        View handling the API request: https://github.com/openedx/edx-platform/blob/46bd8fb12fef49d67a0dc531416ed153f3414cfb/openedx/core/djangoapps/user_authn/views/register.py#L703

        Args:
            url: url of the LMS (base or site). If not specified, uses the base url of the session.
                Defaults to the LMS base.
            **kwargs: dict with form parameters to validate. E.g.:
                    {
                        email=<email>,
                        username=<username>,
                        name=<name>,
                        password=<password>,
                        honor_code=<honor_code>,
                        terms_of_service=<terms_of_service>,
                    }

        Returns:
            dict in the form:
            {
                'validation_decisions': {
                    <field name>: <validation result, or empty if success>,
                    ...
                },
                'username_suggestions': [<username suggestions * 3>]
            }

            Handled by openedx.core.djangoapps.user_authn.views.register.RegistrationValidationView

        """
        response = self._post_json(path=URL_VALIDATION_REGISTRATION, params=kwargs, url=url)

        return response.json()

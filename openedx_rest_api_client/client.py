import json
from typing import List
from urllib.parse import urljoin, urlparse, parse_qs

from openedx_rest_api_client.session import OAuthAPISession

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

URL_BULKENROLL = '/api/bulk_enroll/v1/bulk_enroll/'


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

    def list_all_courses(self, org: str = None) -> List[dict]:
        # pylint: disable=line-too-long
        """
        Get the full list of courses visible to the requesting user.
        Calls the /api/courses/v1/courses LMS endpoint

        Args:
            org: filter by organization

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

        def _get_courses(url, params=None):
            """ Recursively load all pages of course data. """
            response = self.session.get(urljoin(url, URL_COURSES_LIST), params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            next_page_url = data.get("pagination", {}).get("next")
            if next_page_url:
                next_page = urlparse(next_page_url)
                results += _get_courses(next_page_url, parse_qs(next_page.query))

            return results

        params = {"org": org} if org else None
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

        response = self.session.post(
            url=urljoin(url if url else self._base_url, URL_BULKENROLL),
            data=json.dumps(data),
        )
        response.raise_for_status()

        return response.json()

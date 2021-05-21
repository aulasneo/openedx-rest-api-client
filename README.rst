REST API Client for Open edX |CI|_ |Codecov|_
=============================================
.. |CI| image:: https://github.com/aulasneo/openedx-api-client/workflows/Python%20CI/badge.svg?branch=master
.. _CI: https://github.com/aulasneo/openedx-rest-api-client/actions?query=workflow%3A%22Python+CI%22

.. |Codecov| image:: https://codecov.io/github/aulasneo/openedx-api-client/coverage.svg?branch=master
.. _Codecov: https://codecov.io/github/aulasneo/openedx-rest-api-client?branch=master

The REST API client for Open edX REST API allows users to communicate with various edX REST APIs.
It is based on https://github.com/edx/edx-rest-api-client, whith a few differences:

- It does not depend on Django
- What is called 'the client' in edX's version is now called 'session'.
- As the edX's version relies on Django's cache, now the token is stored in memory under the scope of the session object
- The client here encompasses the session, and one function per REST API entry point

Part of the code is also taken from Opencraft's `implementation of the openedx client`_.

.. _implementation of the openedx client: https://gist.github.com/bradenmacdonald/930c7655dca32dc648af9cb0aed4a7c5


Testing
-------
    $ make validate


Usage
~~~~~

The ``OpenedxRESTAPIClient`` object starts a session with the LMS and provides methods to access the Open edX endpoints.

.. code-block:: python

    # create client
    client = OpenedxRESTAPIClient('https://lms.example.com', 'client_id', 'client_secret')

    # get a list of all courses
    courses = client.list_all_courses()

Function Reference
------------------

list_all_courses
~~~~~~~~~~~~~~~~
Get the full list of courses visible to the requesting user.
Calls the /api/courses/v1/courses LMS endpoint

Args:

- org: filter by organization

Returns:

- List of dict in the form:

.. code-block::

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

change_enrollment
~~~~~~~~~~~~~~~~~

Enroll or unenroll (depending on the value of action) the list of emails in the list of courses.
Calls the /api/bulk_enroll/v1/bulk_enroll/ LMS endpoint

Args:

- emails: list of emails to enroll
- courses: list of course ids to enroll
- action: can be 'enroll' or 'unenroll'
- url: url of the LMS (base or site). If not specified, uses the base url of the session. Defaults to the LMS base.
- auto_enroll: if true, the users will be automatically enrolled as soon as they register. Defaults to true.
- email_students: if true, an email will be sent with the update. Defaults to true.
- cohorts: List of cohort names to add the students to.

Returns:

dict in the form:

.. code-block::

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

How to Contribute
-----------------

To contribute, please send a message to `andres@aulasneo.com`_

.. _andres@aulasneo.com: mailto:andres@aulasneo.com
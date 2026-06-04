import json

from openedx_rest_api_client.client import OpenedxRESTAPIClient


def main():

    c = OpenedxRESTAPIClient(
        base_url='https://campus.aulasneo.com',
        client_id='XwHn1NIu7XYZQC1hA347PFPhq4lA3udLS6lBSle9',
        client_secret='36b51mo9sjdOLABkm9A3FcAxS1VmQMuOGZ5mZIVSQAW8AaGMGXakSQFqQ0oWQbTrRZwnVyui0k4l32LNqC3DQToDM0YCxm7SSXxIuzXBe1glN1e5E6gD5CRjjKnO4kHO',
    )
    email = 'test1@aulasneo.com'
    username = 'test1'
    name = 'test1'
    password = 'Prueba123'
    honor_code = 'true'
    terms_of_service = 'true'
    course_id = 'course-v1:edX+DemoX+Demo_Course'

    validation = c.validation_registration(
        email=email,
        username=username,
        name=name,
        password=password,
        honor_code=honor_code,
        terms_of_service=terms_of_service,
        course_id=course_id
    )

    print("\n".join(f"{k}: {v}" for k,v in validation.get('validation_decisions').items() if v))

    # registration_result = c.register_account(
    #     email=email,
    #     username=username,
    #     name=name,
    #     password=password,
    #     honor_code=honor_code,
    #     terms_of_service=terms_of_service,
    #     course_id=course_id
    # )
    #
    # print(f"Error code: {registration_result.get('error_code')}")
    # if registration_result.get('error_code'):
    #     print("\n".join(f"{k}: {v[0].get('user_message')}"
    #                     for k,v in registration_result.items()
    #                     if k not in {'error_code', 'username_suggestions'}))

    enrollment_result = c.change_enrollment(
        emails=[email],
        courses=[course_id],
        action='enroll',
        email_students=False,
    )

    print(enrollment_result)


    # c = OpenedxRESTAPIClient(
    #     base_url='https://lms.aulasneo.com',
    #     client_id='4b2a5d8c9bf317e4f83e',
    #     client_secret='509a00f9403816ad7c0d5fc1d7c67f9a3d217f03',
    # )
    #
    # print(c.change_enrollment(emails=['test@aulasneo.com'], courses=['course-v1:demos+Demo-prev+2017'],
    #                     url='https://demos.aulasneo.com'))

    # result = c.list_all_courses(org='demos', id="course-v1:demos+Demo-prev+2017")

    # print(json.dumps(result, indent=4))

    # for course in result:
    #     print(course['id'])
    #
    # print("{} courses found".format(len(result)))


if __name__ == '__main__':
    main()

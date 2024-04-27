colab_id = '6'
import random
import string
import http.client
import json
import base64
import asyncio
import time


def RandomString(length):
  letters = string.ascii_lowercase
  return ''.join(random.choice(letters) for _ in range(length))


async def get_email_id_api(website, api_key):
  try:
    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": "Basic " + encoded_auth_str}
    url = f"https://{website}.freshdesk.com/api/v2/email/mailboxes"
    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("GET", url, headers=headers)
    response = connection.getresponse()
    bb = response.read().decode()
    list_emails = json.loads(bb)
    if len(list_emails) > 0:
      return list_emails[0]["id"]
    else:
      return -1
  except Exception as ex:
    print(str(ex))  # Uncomment this line to print the exception message
    return -1


async def update_email_api(id, name, website, api_key):
  try:
    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": "Basic " + encoded_auth_str,
        "Content-Type": "application/json"
    }

    url = f"/api/v2/email/mailboxes/{id}"

    nm_email = {
        "name": name,
        "support_email":
        f"{RandomString(8)}@{website}.freshdesk.com"  # Assuming RandomString function is defined elsewhere
    }

    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("PUT", url, json.dumps(nm_email), headers=headers)

    response = connection.getresponse()
    bb = response.read().decode()

    if name in bb:
      return True
    else:
      return False

  except Exception:
    return False


async def add_ticket(to, subject_o, website, api_key):
  try:
    tiket = {
        "description": "welcome to the store",
        "email": to,
        "priority": 3,
        "subject": subject_o,
        "status": 2,
        "source": 2
    }

    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": "Basic " + encoded_auth_str,
        "Content-Type": "application/json"
    }

    url = f"https://{website}.freshdesk.com/api/v2/tickets"

    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("POST", "/api/v2/tickets", json.dumps(tiket), headers)
    response = connection.getresponse()
    return response.read().decode()

  except Exception as ex:
    return "add_ticket_catch=>" + str(ex)


async def send_email_api(api_key, website, body_html, ticket_id, to_mail):
  try:
    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": "Basic " + encoded_auth_str,
        "Content-Type": "application/json"
    }

    url = f"/api/v2/tickets/{ticket_id}/reply"

    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("POST", url,
                       json.dumps({
                           "body": body_html,
                           "cc_emails": []
                       }), headers)

    response = connection.getresponse()
    bb = response.read().decode()

    if to_mail in bb:
      info = json.loads(bb)
      return info
    else:
      print(bb)
      return None

  except Exception as ex:
    return None


async def check_delivered(id, website, api_key):
  try:
    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": "Basic " + encoded_auth_str}

    url = f"/api/v2/tickets/{id}/conversations"

    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("GET", url, headers=headers)

    response = connection.getresponse()
    bb = response.read().decode()

    if "\"email_failure_count\":null" in bb:
      return True
    else:
      return False

  except Exception:
    return False


async def delete_ticket(website, api_key, id):
  try:
    auth_str = f"{api_key}:X"
    encoded_auth_str = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": "Basic " + encoded_auth_str}

    url = f"/api/v2/tickets/{id}"

    connection = http.client.HTTPSConnection(website + ".freshdesk.com")
    connection.request("DELETE", url, headers=headers)

    response = connection.getresponse()
    response.read()  # Consume response, but we don't need it for now

    return ""

  except Exception as ex:
    return str(ex)


async def send_test(website, api_key, from_name, subject, body_html, to_mail,
                    email_id, task_id, id, drop_id):
  if email_id == -1:
    email_id = await get_email_id_api(website, api_key)

  if email_id != -1:
    updated_name = await update_email_api(email_id, from_name, website,
                                          api_key)
    if updated_name:
      add_ticket_response = await add_ticket(to_mail, subject, website,
                                             api_key)

      if "email_config_id" in add_ticket_response:
        result_ticket = json.loads(add_ticket_response)
        send_email_response = await send_email_api(api_key, website, body_html,
                                                   result_ticket["id"],
                                                   to_mail)

        if send_email_response is not None:
          delivered = await check_delivered(result_ticket["id"], website,
                                            api_key)
          if not delivered:
            params = {
                'task_id': task_id,
                'acc_id': id,
                'statu': 'err',
                'drop_id': drop_id,
                'err':
                "Message-not-delivered-from-" + website + "-to-" + to_mail
            }
            response = await change_statu(api, params)

          delete_ticket_response = await delete_ticket(website, api_key,
                                                       result_ticket["id"])
          if delete_ticket_response.strip() != "":
            print("Deleted ticket in website:", delete_ticket_response)
          if delivered:
            return True
          else:
            return False
        else:
          params = {
              'task_id': task_id,
              'acc_id': id,
              'statu': 'err',
              'drop_id': drop_id,
              'err':
              "Error:-Message-not-sent-from-" + website + "-to-" + to_mail
          }
          response = await change_statu(api, params)
          return False
      else:
        params = {
            'task_id': task_id,
            'acc_id': id,
            'statu': 'err',
            'drop_id': drop_id,
            'err': "Error:-Add-ticket-from-" + website + "-to-" + to_mail
        }
        response = await change_statu(api, params)

        return False
    else:
      params = {
          'task_id': task_id,
          'acc_id': id,
          'statu': 'err',
          'drop_id': drop_id,
          'err': "Error:-Update-name-from-" + website + "-to-" + to_mail
      }
      response = await change_statu(api, params)
      return False
  else:
    params = {
        'task_id': task_id,
        'acc_id': id,
        'statu': 'err',
        'drop_id': drop_id,
        'err': "Error:-Email-Not-Found-from-" + website + "-to-" + to_mail
    }
    response = await change_statu(api, params)
    return False


async def get_task(api_link, params):
  try:
    #"localhost/fresh_disk_colab"
    # Encode parameters if provided
    # colab_id
    url = "/api/get_task.php"
    if params:
      params_encoded = "&".join(
          [f"{key}={value}" for key, value in params.items()])
      url += "?" + params_encoded
    # Make a connection to the server
    conn = http.client.HTTPSConnection(api_link)
    # Send a GET request
    conn.request("GET", url)

    # Get the response
    response = conn.getresponse()

    # Read the response data
    if response.status == 200:
      rs = response.read().decode()
      if (rs != "0 results"):
        data = json.loads(rs)
        return data
      else:
        return 'none'
    else:
      return 'none'
  except Exception as ex:
    print("err:" + str(ex))
    return 'none'


async def get_acc(api_link, params):
  try:
    # Encode parameters if provided
    url = "/api/get_account.php"
    if params:
      params_encoded = "&".join(
          [f"{key}={value}" for key, value in params.items()])
      url += "?" + params_encoded
    # Make a connection to the server
    conn = http.client.HTTPSConnection(api_link)
    # Send a GET request
    conn.request("GET", url)

    # Get the response
    response = conn.getresponse()

    # Read the response data
    if response.status == 200:
      rs = response.read().decode()
      if (rs != "0 results"):
        data = json.loads(rs)
        return data
      else:
        return 'none'
    else:
      return 'none'
  except Exception as e:
    return 'none'


async def change_statu(api, params=None):
  # Encode parameters if provided
  url = "/api/change_statu.php"
  if params:
    params_encoded = "&".join(
        [f"{key}={value}" for key, value in params.items()])
    url += "?" + params_encoded

  # Make a connection to the server
  conn = http.client.HTTPSConnection(api)

  try:
    # Send a GET request
    conn.request("GET", url)

    # Get the response
    response = conn.getresponse()

    # Read the response data
    if response.status == 200:
      data = response.read()
      # Decode JSON response
      return data
    else:
      # Print an error message if the request was not successful
      print("Error:", response.status)
      return None
  finally:
    # Close the connection
    conn.close()


async def main(api):
  while (True):
    params = {'colab_id': colab_id}
    data_to_send = await get_task(api, params)
    if (data_to_send != 'none'):
      task_id = data_to_send["task_id"]
      drop_id = data_to_send["drop_id"]
      to = data_to_send["to_email"]
      from_name = data_to_send["from_name"]
      subject = data_to_send["subject"]
      body_html = data_to_send["html_body"]
      sec = 0
      while (True):
        params = {'drop_id': drop_id}
        acc_data = await get_acc(api, params)
        if (acc_data != 'none'):
          id = acc_data["id"]
          website = acc_data["website"]
          api_key = acc_data["api_key"]
          email_id = acc_data["email_id"]
          result = await send_test(website, api_key, from_name, subject,
                                   body_html, to, email_id, task_id, id,
                                   drop_id)
          if (result == True):
            params = {
                'task_id': task_id,
                'acc_id': id,
                'statu': 'delevred',
                'drop_id': drop_id,
                'err': 'none'
            }
            response = await change_statu(api, params)
          print(result)
          break
        else:
          sec = sec + 1
          if (sec > 300):
            break
            time.sleep(2)
    else:
      time.sleep(5)


async def another_function():
  api = "panelapi.mooo.com"
  await main(api)


# Then somewhere in your code, you would await another_function():

asyncio.run(another_function())

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Change password</title>

  <style>
    input.fielderror { outline: 1px solid red; }
  </style>
</head>
<body>

<h1>Change password</h1>

#filter WebSafe
<form  method="post">
  <fieldset>
    <label for="code">
      Code:
      <input id="code" required type="text" name="code" placeholder="Enter change request code here." value="${code, also=''}"
             #if $error_field == "code"
	     class="fielderror"
             #end if
	     >
    </label>
    <label for="new_password1">
      New password:
      <input id="new_password1" required type="password" name="new_password1" placeholder="Enter new password here."
             #if $error_field == "new_password1"
	     class="fielderror"
             #end if
	     >
    </label>
    <label for="new_password2">
      Repeat new password:
      <input id="new_password2" required type="password" name="new_password2" placeholder="Repeat password."
             #if $error_field == "new_password2"
	     class="fielderror"
             #end if
	     >
    </label>
    <input type="submit" value="Submit">
  </fieldset>
</form>

<p style="color:red;">
  #if $error_field == "code"
    The entered request code is invalid.
  #else if $error_field == "new_password1"
    The entered password doesn't match the password rules.
  #else if $error_field == "new_password2"
    The entered passwords have to be equal.
  #end if
</p>
#end filter

</body>
</html>

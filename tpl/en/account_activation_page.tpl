<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Activate user account</title>

  <style>
    input.fielderror { outline: 1px solid red; }
  </style>
</head>
<body>

<h1>Account activation</h1>

#filter WebSafe
<form  method="post">
  <fieldset>
    <label for="code">
      Code:
      <input id="code" required type="text" name="code" placeholder="Enter activation code here." value="${code, also=''}"
             #if $error_field == "code"
	     class="fielderror"
             #end if
	     >
    </label>
    <input type="submit" value="Submit">
  </fieldset>
</form>

<p style="color:red;">
  #if $error_field == "code"
    The entered activation code is invalid.
  #end if
</p>
#end filter

</body>
</html>


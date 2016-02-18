<!DOCTYPE html>
<html>
<head>
  <title>Account activation</title>
</head>
<body>

<h1>Account activation</h1>

#filter WebSafe
<form action="/html/registration/${id, also='"'}" method="post">
  <label for="code">
    Code: <input name="code" placeholder="Enter activation code here." value="${code, also='"'}">
  </label>

  <input type="submit" value="Submit">
</form>
#end filter

</body>
</html>

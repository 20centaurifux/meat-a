-- delete expired records:
delete from request where date_part('epoch'::text, age(timezone('utc'::text, now()), created_on))<=3600;
delete from user_request where date_part('epoch'::text, age(timezone('utc'::text, now()), created_on))<=USER_REQUEST_TIMEOUT;
delete from password_request where date_part('epoch'::text, age(timezone('utc'::text, now()), created_on))<=PASSWORD_REQUEST_TIMEOUT;

CREATE OR REPLACE FUNCTION trg_fn_check_if_email_can_be_changed()
  RETURNS trigger AS
$BODY$
    BEGIN
	if not user_can_change_email(NEW.username, NEW.email, USER_REQUEST_TIMEOUT) then
		raise unique_violation using MESSAGE = 'Duplicate email: ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

CREATE OR REPLACE FUNCTION trg_fn_check_if_username_and_email_are_unique()
  RETURNS trigger AS
$BODY$
    BEGIN
	if user_name_or_email_assigned(NEW.username, NEW.email, USER_REQUEST_TIMEOUT) then
		raise unique_violation using MESSAGE = 'Duplicate user name or email: ' || NEW.username || ', ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

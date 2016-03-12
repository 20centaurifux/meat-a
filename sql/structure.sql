--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: gender_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE gender_type AS ENUM (
    'male',
    'female',
    'trans man',
    'trans woman'
);


--
-- Name: message_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE message_type AS ENUM (
    'recommendation',
    'wrote-comment',
    'voted-object',
    'following',
    'unfollowing'
);


--
-- Name: object_get_comments(uuid, bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION object_get_comments(obj_guid uuid, page bigint, page_size bigint) RETURNS TABLE(id bigint, text character varying, created_on timestamp without time zone, deleted boolean, username character varying)
    LANGUAGE plpgsql
    AS $$

begin	
return query select
    object_comment.id,
    object_comment.comment_text as text,
    object_comment.created_on,
    object_comment.deleted,
    "user".username
   from object_comment
     join "user" on object_comment.user_id="user".id
     where object_guid=obj_guid
  ORDER BY object_comment.created_on desc
  offset page*page_size limit page_size;
end; $$;


--
-- Name: object_get_tagged(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION object_get_tagged(searched_tag character varying) RETURNS TABLE(guid uuid, source character varying, created_on timestamp without time zone, locked boolean, reported boolean, up bigint, down bigint, favorites bigint, comments bigint, tagcount bigint)
    LANGUAGE plpgsql
    AS $$

begin	
	return query select v_objects.*, count(object_guid) as counted from v_objects
		inner join object_tag on object_tag.object_guid=v_objects.guid
		where lower(tag)=lower(searched_tag)
		group by v_objects.guid, v_objects.source, v_objects.created_on, v_objects.locked, v_objects.reported, v_objects.up, v_objects.down, v_objects.favorites, v_objects.comments
		order by counted desc, created_on desc;
end; $$;


--
-- Name: trg_fn_check_if_email_can_be_changed(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_check_if_email_can_be_changed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if not user_can_change_email(NEW.username, NEW.email, 600) then
		raise unique_violation using MESSAGE = 'Duplicate email: ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_check_if_username_and_email_are_unique(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_check_if_username_and_email_are_unique() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if user_name_or_email_assigned(NEW.username, NEW.email, 600) then
		raise unique_violation using MESSAGE = 'Duplicate user name or email: ' || NEW.username || ', ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_create_comment_message(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_create_comment_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
	is_protected boolean;
	friend_id bigint;
    
    BEGIN
	select protected
		into is_protected
		from "user"
		where id=NEW.user_id;

	for friend_id in select * from user_get_follower_ids(NEW.user_id) loop
		insert into "message" ("receiver_id", "type", "target", "source") values (friend_id, 'wrote-comment', NEW.id, NEW.user_id::varchar);
	end loop;

	if not is_protected then
		insert into "public_message" ("type", "target", "source") values ('wrote-comment', NEW.id, NEW.user_id::varchar);
        end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_create_friendship_message(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_create_friendship_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source") values (NEW.friend_id, 'following', NEW.user_id::varchar);
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_create_recommendation_message(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_create_recommendation_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source", "target") values (NEW.receiver_id, 'recommendation', NEW.user_id::varchar, NEW.object_guid);
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_destroy_friendship_message(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_destroy_friendship_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source") values (OLD.friend_id, 'unfollowing', OLD.user_id::varchar);
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_generate_vote_messages(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_generate_vote_messages() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
	is_protected boolean;
	friend_id bigint;
    
    BEGIN
	select protected
		into is_protected
		from "user"
		where id=NEW.user_id;

	for friend_id in select * from user_get_follower_ids(NEW.user_id) loop
		insert into "message" ("receiver_id", "type", "target", "source") values (friend_id, 'voted-object', NEW.object_guid, NEW.user_id::varchar);
	end loop;

	if not is_protected then
		insert into "public_message" ("type", "target", "source") values ('voted-object', NEW.object_guid, NEW.user_id::varchar);
        end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_update_iusername_and_iemail(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_update_iusername_and_iemail() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	NEW.iusername=lower(NEW.username);
	NEW.iemail=lower(NEW.email);

	return NEW;
    END;
$$;


--
-- Name: trg_fn_update_object_timestamps(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_update_object_timestamps() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if not OLD.deleted and NEW.deleted then
		NEW.deleted_on = timezone('utc'::text, now());
	elsif OLD.deleted and not NEW.deleted then
		NEW.deleted_on = null;
	end if;

	if not OLD.reported and NEW.reported then
		NEW.reported_on = timezone('utc'::text, now());
	elsif OLD.reported and not NEW.reported then
		NEW.reported_on = null;
	end if;

	if not OLD.locked and NEW.locked then
		NEW.locked_on = timezone('utc'::text, now());
	elsif OLD.locked and not NEW.locked then
		NEW.locked_on = null;
	end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: trg_fn_update_user_timestamps(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION trg_fn_update_user_timestamps() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if not OLD.blocked and NEW.blocked then
		NEW.blocked_on = timezone('utc'::text, now());
	elsif OLD.blocked and not NEW.blocked then
		NEW.blocked_on = null;
	end if;

	if not OLD.deleted and NEW.deleted then
		NEW.deleted_on = timezone('utc'::text, now());
	elsif OLD.deleted and not NEW.deleted then
		NEW.deleted_on = null;
	end if;
        
        RETURN NEW;
    END;
$$;


--
-- Name: user_activate(character varying, character varying, character varying, character varying, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_activate(id character varying, code character varying, password character varying, salt character varying, timeout bigint) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
declare
	found_username varchar;
	found_email varchar;
	pk bigint default null;

begin
	select
		"username", "email"
		into found_username, found_email
		from "v_user_requests"
		where "request_id"=id and "request_code"=code and datediff<=timeout;

	if found_username is not null and found_email is not null then
		pk := nextval('seq_user_id');
		insert into "user" ("id", "username", "email", "password", "salt") values (pk, found_username, found_email, password, salt);
		delete from "user_request" where "request_id"=id and "request_code"=code;
	end if; 
	
	return pk;
end; $$;


--
-- Name: user_can_change_email(character varying, character varying, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_can_change_email(account_name character varying, new_email character varying, timeout bigint) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	request_count bigint default 0;
	user_count bigint default 0;

begin
	select
		count(request_id)
		into request_count
		from "v_user_requests"
		where "iemail"=lower(new_email) and datediff<=timeout;

	select
		count(id)
		into user_count
		from "user" where "iusername"<>lower(account_name) and "iemail"=lower(new_email);
	
	return (select request_count = 0 and user_count = 0);
end; $$;


--
-- Name: user_get_follower_ids(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_get_follower_ids(uid bigint) RETURNS SETOF bigint
    LANGUAGE plpgsql
    AS $$

begin	
	return query select user_id
		from user_friendship
		inner join "user" on id=user_id
		where friend_id=uid and not deleted and not blocked;
end; $$;


--
-- Name: user_name_or_email_assigned(character varying, character varying, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_name_or_email_assigned(user_to_test character varying, email_to_test character varying, timeout bigint) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	request_count bigint;
	user_count bigint;
	
begin
	select
		count(request_id)
		into request_count
		from "v_user_requests"
		where ("iusername"=lower(user_to_test) or "iemail"=lower(email_to_test)) and datediff<=timeout;
	select
		count(id)
		into user_count
		from "user" where "iusername"=lower(user_to_test) or "iemail"=lower(email_to_test);

	return (select request_count > 0 or user_count > 0);
end; $$;


--
-- Name: user_reset_password(character varying, character varying, character varying, character varying, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_reset_password(req_id character varying, req_code character varying, new_password character varying, new_salt character varying, timeout bigint) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	found_user_id bigint;
	success boolean default false;

begin
	select
		"user_id"
		into found_user_id
		from "v_password_requests"
		where "request_id"=req_id and "request_code"=req_code and datediff<=datediff;

	if found_user_id is not null then
		update "user" set "password"=new_password, "salt"=new_salt where "id"=found_user_id;
		delete from "password_request" where "request_id"=req_id and request_code=req_code;
		success := true;
	end if; 
	
	return success;
end; $$;


--
-- Name: seq_mail_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_mail_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: mail; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE mail (
    id bigint DEFAULT nextval('seq_mail_id'::regclass),
    receiver_id bigint,
    subject character varying(64) NOT NULL,
    body character varying(4096) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()),
    sent boolean DEFAULT false,
    sent_on timestamp without time zone,
    mail character varying(128)
);


--
-- Name: seq_message_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_message_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: message; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE message (
    id integer DEFAULT nextval('seq_message_id'::regclass) NOT NULL,
    receiver_id integer NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    read_status boolean DEFAULT false NOT NULL,
    read_on timestamp without time zone,
    target character varying(64),
    type message_type NOT NULL,
    source character varying(64) NOT NULL
);


--
-- Name: object; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE object (
    guid uuid NOT NULL,
    source character varying(512) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    deleted boolean DEFAULT false NOT NULL,
    deleted_on timestamp without time zone,
    reported boolean DEFAULT false,
    reported_on timestamp without time zone,
    locked boolean DEFAULT false,
    locked_on timestamp without time zone
);


--
-- Name: seq_comment_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_comment_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: object_comment; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE object_comment (
    id bigint DEFAULT nextval('seq_comment_id'::regclass) NOT NULL,
    user_id bigint NOT NULL,
    object_guid uuid NOT NULL,
    comment_text character varying(4096) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    deleted boolean DEFAULT false NOT NULL,
    deleted_on timestamp without time zone
);


--
-- Name: object_score; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE object_score (
    object_guid uuid NOT NULL,
    user_id integer NOT NULL,
    up boolean NOT NULL
);


--
-- Name: object_tag; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE object_tag (
    user_id integer NOT NULL,
    object_guid uuid NOT NULL,
    tag character varying(32) NOT NULL
);


--
-- Name: password_request; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE password_request (
    request_id character varying(128) NOT NULL,
    request_code character varying(128) NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: seq_public_message_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_public_message_id
    START WITH 17
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: public_message; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE public_message (
    id integer DEFAULT nextval('seq_public_message_id'::regclass) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    target character varying(64),
    type message_type NOT NULL,
    source character varying(64) NOT NULL
);


--
-- Name: seq_request_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_request_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: request; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE request (
    id bigint DEFAULT nextval('seq_request_id'::regclass),
    user_id bigint,
    address character varying(64) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now())
);


--
-- Name: request_count; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE request_count (
    count bigint
);


--
-- Name: seq_user_id; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE seq_user_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE "user" (
    id integer DEFAULT nextval('seq_user_id'::regclass) NOT NULL,
    username character varying(32) NOT NULL,
    email character varying(64) NOT NULL,
    firstname character varying,
    lastname character varying(64),
    language character varying(8),
    gender gender_type,
    password character varying(128),
    salt character varying(128) NOT NULL,
    blocked boolean DEFAULT false NOT NULL,
    deleted boolean DEFAULT false NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    blocked_on timestamp without time zone,
    deleted_on timestamp without time zone,
    iusername character varying(32),
    iemail character varying(64),
    protected boolean DEFAULT true,
    avatar character varying(512)
);


--
-- Name: user_favorite; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE user_favorite (
    object_guid uuid NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


--
-- Name: user_friendship; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE user_friendship (
    user_id bigint NOT NULL,
    friend_id bigint NOT NULL
);


--
-- Name: user_recommendation; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE user_recommendation (
    object_guid uuid NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()),
    receiver_id bigint NOT NULL
);


--
-- Name: user_request; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE user_request (
    request_id character varying(128) NOT NULL,
    request_code character varying(128) NOT NULL,
    username character varying(32) NOT NULL,
    email character varying(64) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    iusername character varying(32),
    iemail character varying(64)
);


--
-- Name: v_objects; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_objects AS
 SELECT object.guid,
    object.source,
    object.created_on,
    object.locked,
    object.reported,
    ( SELECT count(*) AS count
           FROM object_score
          WHERE (object_score.up AND (object_score.object_guid = object.guid))) AS up,
    ( SELECT count(*) AS count
           FROM object_score
          WHERE ((NOT object_score.up) AND (object_score.object_guid = object.guid))) AS down,
    ( SELECT count(*) AS count
           FROM user_favorite
          WHERE (user_favorite.object_guid = object.guid)) AS favorites,
    ( SELECT count(*) AS count
           FROM object_comment
          WHERE (object_comment.object_guid = object.guid)) AS comments
   FROM object
  WHERE (NOT object.deleted)
  GROUP BY object.guid, object.source, object.created_on, object.locked, object.reported;


--
-- Name: v_password_requests; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_password_requests AS
 SELECT password_request.request_id,
    password_request.request_code,
    password_request.user_id,
    password_request.created_on,
    date_part('epoch'::text, age(timezone('utc'::text, now()), password_request.created_on)) AS datediff
   FROM password_request;


--
-- Name: v_popular_objects; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_popular_objects AS
 SELECT v_objects.guid,
    v_objects.source,
    v_objects.created_on,
    v_objects.locked,
    v_objects.reported,
    v_objects.up,
    v_objects.down,
    v_objects.favorites,
    v_objects.comments
   FROM v_objects
  ORDER BY ((v_objects.up - v_objects.down) + v_objects.favorites) DESC, v_objects.created_on DESC;


--
-- Name: v_random_objects; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_random_objects AS
 SELECT v_objects.guid,
    v_objects.source,
    v_objects.created_on,
    v_objects.locked,
    v_objects.reported,
    v_objects.up,
    v_objects.down,
    v_objects.favorites,
    v_objects.comments
   FROM v_objects
  ORDER BY random();


--
-- Name: v_recommendations; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_recommendations AS
 SELECT sender_table.iusername AS sender,
    receiver_table.iusername AS receiver,
    user_recommendation.created_on AS recommended_on,
    v_objects.guid,
    v_objects.source,
    v_objects.created_on,
    v_objects.locked,
    v_objects.reported,
    v_objects.up,
    v_objects.down,
    v_objects.favorites,
    v_objects.comments
   FROM (((v_objects
     JOIN user_recommendation ON ((user_recommendation.object_guid = v_objects.guid)))
     JOIN "user" sender_table ON ((user_recommendation.user_id = sender_table.id)))
     JOIN "user" receiver_table ON ((user_recommendation.receiver_id = receiver_table.id)));


--
-- Name: v_tags; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_tags AS
 SELECT object_tag.tag,
    count(v_objects.guid) AS count
   FROM (object_tag
     JOIN v_objects ON ((object_tag.object_guid = v_objects.guid)))
  GROUP BY object_tag.tag
  ORDER BY count(v_objects.guid) DESC;


--
-- Name: v_user_requests; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_user_requests AS
 SELECT user_request.request_id,
    user_request.request_code,
    user_request.username,
    user_request.email,
    user_request.created_on,
    user_request.iusername,
    user_request.iemail,
    date_part('epoch'::text, age(timezone('utc'::text, now()), user_request.created_on)) AS datediff
   FROM user_request;


--
-- Name: password_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT password_request_unique_request_id UNIQUE (request_id);


--
-- Name: pk_message; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY message
    ADD CONSTRAINT pk_message PRIMARY KEY (id);


--
-- Name: pk_object; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY object
    ADD CONSTRAINT pk_object PRIMARY KEY (guid);


--
-- Name: pk_object_comment; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT pk_object_comment PRIMARY KEY (id);


--
-- Name: pk_object_score; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT pk_object_score PRIMARY KEY (object_guid, user_id);


--
-- Name: pk_object_tag; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT pk_object_tag PRIMARY KEY (user_id, object_guid, tag);


--
-- Name: pk_password_request_id; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT pk_password_request_id PRIMARY KEY (request_id, request_code);


--
-- Name: pk_public_message; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY public_message
    ADD CONSTRAINT pk_public_message PRIMARY KEY (id);


--
-- Name: pk_request; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT pk_request PRIMARY KEY (request_id, request_code);


--
-- Name: pk_user_favorite; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT pk_user_favorite PRIMARY KEY (object_guid, user_id);


--
-- Name: pk_user_friendship; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT pk_user_friendship PRIMARY KEY (user_id, friend_id);


--
-- Name: pk_user_id; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT pk_user_id PRIMARY KEY (id);


--
-- Name: pk_user_recommendation; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT pk_user_recommendation PRIMARY KEY (object_guid, user_id, receiver_id);


--
-- Name: user_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT user_request_unique_request_id UNIQUE (request_id);


--
-- Name: fk_object_guid; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fk_object_guid ON object_comment USING btree (object_guid);


--
-- Name: fk_user_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fk_user_id ON object_comment USING btree (user_id);


--
-- Name: fki_favorite_user_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_favorite_user_id ON user_favorite USING btree (user_id);


--
-- Name: fki_mail_receiver_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_mail_receiver_id ON mail USING btree (receiver_id);


--
-- Name: fki_object_recommendation_receiver_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_object_recommendation_receiver_id ON user_recommendation USING btree (receiver_id);


--
-- Name: fki_object_recommendation_user_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_object_recommendation_user_id ON user_recommendation USING btree (user_id);


--
-- Name: fki_object_tag_object_guid; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_object_tag_object_guid ON object_tag USING btree (object_guid);


--
-- Name: fki_receiver_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_receiver_id ON message USING btree (receiver_id);


--
-- Name: fki_user_friendship_friendship_id; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX fki_user_friendship_friendship_id ON user_friendship USING btree (friend_id);


--
-- Name: trg_check_user_request_username_and_email; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_check_user_request_username_and_email BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_username_and_email_are_unique();


--
-- Name: trg_object_comment_create_message; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_object_comment_create_message AFTER INSERT ON object_comment FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_comment_message();


--
-- Name: trg_object_score_create_message; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_object_score_create_message AFTER INSERT ON object_score FOR EACH ROW EXECUTE PROCEDURE trg_fn_generate_vote_messages();


--
-- Name: trg_object_update_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_object_update_timestamps BEFORE UPDATE ON object FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_object_timestamps();


--
-- Name: trg_update_user_request_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_update_user_request_iusername_and_iemail BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- Name: trg_user_check_email; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_check_email BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_email_can_be_changed();


--
-- Name: trg_user_create_recommendation_message; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_create_recommendation_message BEFORE INSERT ON user_recommendation FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_recommendation_message();


--
-- Name: trg_user_friendship_destroyed; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_friendship_destroyed AFTER DELETE ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_destroy_friendship_message();


--
-- Name: trg_user_friendship_inserted; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_friendship_inserted AFTER INSERT ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_friendship_message();


--
-- Name: trg_user_update_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_update_iusername_and_iemail BEFORE INSERT OR UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- Name: trg_user_update_timestamps; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_update_timestamps BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_user_timestamps();


--
-- Name: fk_message_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY message
    ADD CONSTRAINT fk_message_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- Name: fk_object_comment_author_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_author_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: fk_object_comment_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- Name: fk_object_score_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- Name: fk_object_score_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: fk_object_tag_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- Name: fk_object_tag_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: fk_user_favorite_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- Name: fk_user_favorite_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: fk_user_friendship_friendship_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT fk_user_friendship_friendship_id FOREIGN KEY (friend_id) REFERENCES "user"(id);


--
-- Name: fk_user_recommendation_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- Name: fk_user_recommendation_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- Name: fk_user_recommendation_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: mail_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY mail
    ADD CONSTRAINT mail_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- Name: user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY request
    ADD CONSTRAINT user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: -
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--


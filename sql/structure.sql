--
-- PostgreSQL database dump
--

-- Dumped from database version 9.4.5
-- Dumped by pg_dump version 9.4.5
-- Started on 2016-01-21 17:29:13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 197 (class 3079 OID 11855)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2211 (class 0 OID 0)
-- Dependencies: 197
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- TOC entry 606 (class 1247 OID 16731)
-- Name: gender_type; Type: TYPE; Schema: public; Owner: meat-a
--

CREATE TYPE gender_type AS ENUM (
    'male',
    'female',
    'trans man',
    'trans woman'
);


ALTER TYPE gender_type OWNER TO "meat-a";

--
-- TOC entry 609 (class 1247 OID 16748)
-- Name: message_type; Type: TYPE; Schema: public; Owner: meat-a
--

CREATE TYPE message_type AS ENUM (
    'recommendation',
    'wrote-comment',
    'voted-object',
    'following',
    'unfollowing'
);


ALTER TYPE message_type OWNER TO "meat-a";

--
-- TOC entry 223 (class 1255 OID 17126)
-- Name: object_get_comments(uuid, bigint, bigint); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.object_get_comments(obj_guid uuid, page bigint, page_size bigint) OWNER TO "meat-a";

--
-- TOC entry 221 (class 1255 OID 17033)
-- Name: object_get_tagged(character varying); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.object_get_tagged(searched_tag character varying) OWNER TO "meat-a";

--
-- TOC entry 215 (class 1255 OID 16617)
-- Name: trg_fn_check_if_email_can_be_changed(); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION trg_fn_check_if_email_can_be_changed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if not user_can_change_email(NEW.username, NEW.email) then
		raise unique_violation using MESSAGE = 'Duplicate email: ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$$;


ALTER FUNCTION public.trg_fn_check_if_email_can_be_changed() OWNER TO "meat-a";

--
-- TOC entry 213 (class 1255 OID 16606)
-- Name: trg_fn_check_if_username_and_email_are_unique(); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION trg_fn_check_if_username_and_email_are_unique() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	if user_name_or_email_assigned(NEW.username, NEW.email) then
		raise unique_violation using MESSAGE = 'Duplicate user name or email: ' || NEW.username || ', ' || NEW.email;
	end if;
        
        RETURN NEW;
    END;
$$;


ALTER FUNCTION public.trg_fn_check_if_username_and_email_are_unique() OWNER TO "meat-a";

--
-- TOC entry 225 (class 1255 OID 24576)
-- Name: trg_fn_create_comment_message(); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.trg_fn_create_comment_message() OWNER TO "meat-a";

--
-- TOC entry 218 (class 1255 OID 16583)
-- Name: trg_fn_create_friendship_message(); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION trg_fn_create_friendship_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source") values (NEW.friend_id, 'following', NEW.user_id::varchar);
        
        RETURN NEW;
    END;
$$;


ALTER FUNCTION public.trg_fn_create_friendship_message() OWNER TO "meat-a";

--
-- TOC entry 224 (class 1255 OID 17150)
-- Name: trg_fn_create_recommendation_message(); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION trg_fn_create_recommendation_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source", "target") values (NEW.receiver_id, 'recommendation', NEW.user_id::varchar, NEW.object_guid);
        
        RETURN NEW;
    END;
$$;


ALTER FUNCTION public.trg_fn_create_recommendation_message() OWNER TO "meat-a";

--
-- TOC entry 217 (class 1255 OID 16584)
-- Name: trg_fn_destroy_friendship_message(); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION trg_fn_destroy_friendship_message() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
	insert into "message" ("receiver_id", "type", "source") values (OLD.friend_id, 'unfollowing', OLD.user_id::varchar);
        
        RETURN NEW;
    END;
$$;


ALTER FUNCTION public.trg_fn_destroy_friendship_message() OWNER TO "meat-a";

--
-- TOC entry 226 (class 1255 OID 17072)
-- Name: trg_fn_generate_vote_messages(); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.trg_fn_generate_vote_messages() OWNER TO "meat-a";

--
-- TOC entry 210 (class 1255 OID 16626)
-- Name: trg_fn_update_iusername_and_iemail(); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.trg_fn_update_iusername_and_iemail() OWNER TO "meat-a";

--
-- TOC entry 220 (class 1255 OID 16775)
-- Name: trg_fn_update_object_timestamps(); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.trg_fn_update_object_timestamps() OWNER TO "meat-a";

--
-- TOC entry 216 (class 1255 OID 16632)
-- Name: trg_fn_update_user_timestamps(); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.trg_fn_update_user_timestamps() OWNER TO "meat-a";

--
-- TOC entry 214 (class 1255 OID 16636)
-- Name: user_activate(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION user_activate(id character varying, code character varying, password character varying, salt character varying) RETURNS bigint
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
		from "user_request" where "request_id"=id and "request_code"=code and date_part('hours', created_on - timezone('utc'::text, now())) <= 1;

	if found_username is not null and found_email is not null then
		pk := nextval('seq_user_id');
		insert into "user" ("id", "username", "email", "password", "salt") values (pk, found_username, found_email, password, salt);
		delete from "user_request" where "request_id"=id and "request_code"=code;
	end if; 
	
	return pk;
end; $$;


ALTER FUNCTION public.user_activate(id character varying, code character varying, password character varying, salt character varying) OWNER TO "meat-a";

--
-- TOC entry 219 (class 1255 OID 16671)
-- Name: user_can_change_email(character varying, character varying); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION user_can_change_email(account_name character varying, new_email character varying) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	request_count bigint default 0;
	user_count bigint default 0;

begin
	select
		count(request_id)
		into request_count
		from "user_request" where "iemail"=lower(new_email) and date_part('hours', created_on - timezone('utc'::text, now())) <= 1;

	select
		count(id)
		into user_count
		from "user" where "iusername"<>lower(account_name) and "iemail"=lower(new_email);
	
	return (select request_count = 0 and user_count = 0);
end; $$;


ALTER FUNCTION public.user_can_change_email(account_name character varying, new_email character varying) OWNER TO "meat-a";

--
-- TOC entry 222 (class 1255 OID 17045)
-- Name: user_get_follower_ids(bigint); Type: FUNCTION; Schema: public; Owner: meat-a
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


ALTER FUNCTION public.user_get_follower_ids(uid bigint) OWNER TO "meat-a";

--
-- TOC entry 212 (class 1255 OID 16635)
-- Name: user_name_or_email_assigned(character varying, character varying); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION user_name_or_email_assigned(user_to_test character varying, email_to_test character varying) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	request_count bigint;
	user_count bigint;
	
begin
	select
		count(request_id)
		into request_count
		from "user_request" where ("iusername"=lower(user_to_test) or "iemail"=lower(email_to_test)) and date_part('hours', created_on - timezone('utc'::text, now())) <= 1;
	select
		count(id)
		into user_count
		from "user" where "iusername"=lower(user_to_test) or "iemail"=lower(email_to_test);

	return (select request_count > 0 or user_count > 0);
end; $$;


ALTER FUNCTION public.user_name_or_email_assigned(user_to_test character varying, email_to_test character varying) OWNER TO "meat-a";

--
-- TOC entry 211 (class 1255 OID 16682)
-- Name: user_reset_password(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: meat-a
--

CREATE FUNCTION user_reset_password(req_id character varying, req_code character varying, new_password character varying, new_salt character varying) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare
	found_user_id bigint;
	success boolean default false;

begin
	select
		"user_id"
		into found_user_id
		from "password_request" where "request_id"=req_id and "request_code"=req_code and date_part('hours', created_on - timezone('utc'::text, now())) <= 1;

	if found_user_id is not null then
		update "user" set "password"=new_password, "salt"=new_salt where "id"=found_user_id;
		delete from "password_request" where "request_id"=req_id and request_code=req_code;
		success := true;
	end if; 
	
	return success;
end; $$;


ALTER FUNCTION public.user_reset_password(req_id character varying, req_code character varying, new_password character varying, new_salt character varying) OWNER TO "meat-a";

--
-- TOC entry 195 (class 1259 OID 32768)
-- Name: seq_mail_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_mail_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_mail_id OWNER TO "meat-a";

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 196 (class 1259 OID 32770)
-- Name: mail; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE mail OWNER TO "meat-a";

--
-- TOC entry 183 (class 1259 OID 16528)
-- Name: seq_message_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_message_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_message_id OWNER TO "meat-a";

--
-- TOC entry 184 (class 1259 OID 16543)
-- Name: message; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE message OWNER TO "meat-a";

--
-- TOC entry 178 (class 1259 OID 16449)
-- Name: object; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE object OWNER TO "meat-a";

--
-- TOC entry 182 (class 1259 OID 16491)
-- Name: seq_comment_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_comment_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_comment_id OWNER TO "meat-a";

--
-- TOC entry 181 (class 1259 OID 16488)
-- Name: object_comment; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE object_comment OWNER TO "meat-a";

--
-- TOC entry 179 (class 1259 OID 16466)
-- Name: object_score; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE object_score (
    object_guid uuid NOT NULL,
    user_id integer NOT NULL,
    up boolean NOT NULL
);


ALTER TABLE object_score OWNER TO "meat-a";

--
-- TOC entry 180 (class 1259 OID 16477)
-- Name: object_tag; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE object_tag (
    user_id integer NOT NULL,
    object_guid uuid NOT NULL,
    tag character varying(32) NOT NULL
);


ALTER TABLE object_tag OWNER TO "meat-a";

--
-- TOC entry 185 (class 1259 OID 16672)
-- Name: password_request; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE password_request (
    request_id character varying(128) NOT NULL,
    request_code character varying(128) NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


ALTER TABLE password_request OWNER TO "meat-a";

--
-- TOC entry 191 (class 1259 OID 17078)
-- Name: seq_public_message_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_public_message_id
    START WITH 17
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_public_message_id OWNER TO "meat-a";

--
-- TOC entry 192 (class 1259 OID 17080)
-- Name: public_message; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE public_message (
    id integer DEFAULT nextval('seq_public_message_id'::regclass) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    target character varying(64),
    type message_type NOT NULL,
    source character varying(64) NOT NULL
);


ALTER TABLE public_message OWNER TO "meat-a";

--
-- TOC entry 176 (class 1259 OID 16431)
-- Name: seq_user_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_user_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_user_id OWNER TO "meat-a";

--
-- TOC entry 175 (class 1259 OID 16411)
-- Name: user; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE "user" OWNER TO "meat-a";

--
-- TOC entry 186 (class 1259 OID 16786)
-- Name: user_favorite; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE user_favorite (
    object_guid uuid NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


ALTER TABLE user_favorite OWNER TO "meat-a";

--
-- TOC entry 177 (class 1259 OID 16444)
-- Name: user_friendship; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE user_friendship (
    user_id bigint NOT NULL,
    friend_id bigint NOT NULL
);


ALTER TABLE user_friendship OWNER TO "meat-a";

--
-- TOC entry 193 (class 1259 OID 17127)
-- Name: user_recommendation; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE user_recommendation (
    object_guid uuid NOT NULL,
    user_id bigint NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()),
    receiver_id bigint NOT NULL
);


ALTER TABLE user_recommendation OWNER TO "meat-a";

--
-- TOC entry 174 (class 1259 OID 16403)
-- Name: user_request; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
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


ALTER TABLE user_request OWNER TO "meat-a";

--
-- TOC entry 187 (class 1259 OID 17016)
-- Name: v_objects; Type: VIEW; Schema: public; Owner: meat-a
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


ALTER TABLE v_objects OWNER TO "meat-a";

--
-- TOC entry 188 (class 1259 OID 17021)
-- Name: v_popular_objects; Type: VIEW; Schema: public; Owner: meat-a
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


ALTER TABLE v_popular_objects OWNER TO "meat-a";

--
-- TOC entry 189 (class 1259 OID 17026)
-- Name: v_random_objects; Type: VIEW; Schema: public; Owner: meat-a
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


ALTER TABLE v_random_objects OWNER TO "meat-a";

--
-- TOC entry 194 (class 1259 OID 17152)
-- Name: v_recommendations; Type: VIEW; Schema: public; Owner: meat-a
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


ALTER TABLE v_recommendations OWNER TO "meat-a";

--
-- TOC entry 190 (class 1259 OID 17038)
-- Name: v_tags; Type: VIEW; Schema: public; Owner: meat-a
--

CREATE VIEW v_tags AS
 SELECT object_tag.tag,
    count(v_objects.guid) AS count
   FROM (object_tag
     JOIN v_objects ON ((object_tag.object_guid = v_objects.guid)))
  GROUP BY object_tag.tag
  ORDER BY count(v_objects.guid) DESC;


ALTER TABLE v_tags OWNER TO "meat-a";

--
-- TOC entry 2203 (class 0 OID 32770)
-- Dependencies: 196
-- Data for Name: mail; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY mail (id, receiver_id, subject, body, created_on, sent, sent_on, mail) FROM stdin;
13	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:01:36.594	f	\N	\N
14	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:02:06.905	f	\N	\N
15	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:03:00.488	f	\N	\N
16	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:03:33.111	f	\N	\N
17	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:05:05.009	f	\N	\N
18	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/user/snafu/password/reset\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:05:18.536	f	\N	\N
19	24	Password changed: snafu\n	Dear snafu,\n\nHerewith we want to inform you that someone (hopefully you!) has changed\nyour password.\n\n\nKind regards,\n\nYour staff\n	2016-01-21 07:05:18.833	f	\N	\N
20	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/password/reset/alE2ag==?code=UWczOA==\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:09:05.66	f	\N	\N
21	24	Password changed: snafu\n	Dear snafu,\n\nHerewith we want to inform you that someone (hopefully you!) has changed\nyour password.\n\n\nKind regards,\n\nYour staff\n	2016-01-21 07:09:05.957	f	\N	\N
22	24	New password requested: snafu\n	Dear snafu,\n\nSomeone (hopefully you) has requested to reset your password.\n\nIf you want to change the password please visit the following website:\n\nhttp://localhost:8000/password/reset/bTlUQQ==?code=YWtyRw==\n\n\nIf you should have any further questions, please don't hesitate to contact\nus,\n\n\nYour staff\n	2016-01-21 07:11:56.946	f	\N	\N
23	24	Password changed: snafu\n	Dear snafu,\n\nHerewith we want to inform you that someone (hopefully you!) has changed\nyour password.\n\n\nKind regards,\n\nYour staff\n	2016-01-21 07:11:57.321	f	\N	\N
\.


--
-- TOC entry 2196 (class 0 OID 16543)
-- Dependencies: 184
-- Data for Name: message; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY message (id, receiver_id, created_on, read_status, read_on, target, type, source) FROM stdin;
36	21	2016-01-19 16:31:21.184	f	\N	\N	following	20
37	20	2016-01-19 16:31:21.372	f	\N	\N	following	21
38	21	2016-01-19 16:31:55.514	f	\N	25ceff6e-3626-4a50-aaba-fa90b18b7984	voted-object	20
39	21	2016-01-19 16:33:29.112	f	\N	8	wrote-comment	20
40	20	2016-01-19 16:33:57.207	f	\N	9	wrote-comment	21
41	20	2016-01-19 16:35:47.482	f	\N	10	wrote-comment	21
42	20	2016-01-20 06:38:36.525	f	\N	11	wrote-comment	21
43	20	2016-01-20 07:01:03.029	f	\N	12	wrote-comment	21
44	20	2016-01-20 07:01:09.597	f	\N	13	wrote-comment	21
\.


--
-- TOC entry 2190 (class 0 OID 16449)
-- Dependencies: 178
-- Data for Name: object; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object (guid, source, created_on, deleted, deleted_on, reported, reported_on, locked, locked_on) FROM stdin;
25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-12 18:08:55.994	f	\N	f	\N	f	\N
5e9c9ffe-d4c3-4c1a-987e-42ee560990e0	bar	2016-01-12 18:18:17.548	f	\N	f	\N	f	\N
15ceff6e-3626-4a50-aaba-fa90b18b7984	fnord	2016-01-15 06:44:24.912	f	\N	f	\N	f	\N
\.


--
-- TOC entry 2193 (class 0 OID 16488)
-- Dependencies: 181
-- Data for Name: object_comment; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_comment (id, user_id, object_guid, comment_text, created_on, deleted, deleted_on) FROM stdin;
1	20	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-13 07:01:15.306	f	\N
2	20	25ceff6e-3626-4a50-aaba-fa90b18b7984	bar	2016-01-13 07:01:23.082	f	\N
3	20	25ceff6e-3626-4a50-aaba-fa90b18b7984	foobar	2016-01-13 07:01:27.331	f	\N
5	20	25ceff6e-3626-4a50-aaba-fa90b18b7984	hyperwurst	2016-01-15 15:50:12.76	f	\N
6	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	this is a test	2016-01-19 15:34:26.752	f	\N
7	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	this is a test	2016-01-19 15:45:27.755	f	\N
8	20	25ceff6e-3626-4a50-aaba-fa90b18b7984	Maximaler Megaschrott	2016-01-19 16:33:29.112	f	\N
9	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-19 16:33:57.207	f	\N
10	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-19 16:35:47.482	f	\N
11	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-20 06:38:36.525	f	\N
12	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-20 07:01:03.029	f	\N
13	21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-20 07:01:09.597	f	\N
\.


--
-- TOC entry 2191 (class 0 OID 16466)
-- Dependencies: 179
-- Data for Name: object_score; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_score (object_guid, user_id, up) FROM stdin;
25ceff6e-3626-4a50-aaba-fa90b18b7984	20	t
\.


--
-- TOC entry 2192 (class 0 OID 16477)
-- Dependencies: 180
-- Data for Name: object_tag; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_tag (user_id, object_guid, tag) FROM stdin;
20	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo
20	25ceff6e-3626-4a50-aaba-fa90b18b7984	bar
21	25ceff6e-3626-4a50-aaba-fa90b18b7984	foo
21	5e9c9ffe-d4c3-4c1a-987e-42ee560990e0	foo
\.


--
-- TOC entry 2197 (class 0 OID 16672)
-- Dependencies: 185
-- Data for Name: password_request; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY password_request (request_id, request_code, user_id, created_on) FROM stdin;
\.


--
-- TOC entry 2200 (class 0 OID 17080)
-- Dependencies: 192
-- Data for Name: public_message; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY public_message (id, created_on, target, type, source) FROM stdin;
19	2016-01-19 16:31:55.514	25ceff6e-3626-4a50-aaba-fa90b18b7984	voted-object	20
20	2016-01-19 16:33:29.112	8	wrote-comment	20
\.


--
-- TOC entry 2212 (class 0 OID 0)
-- Dependencies: 182
-- Name: seq_comment_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_comment_id', 13, true);


--
-- TOC entry 2213 (class 0 OID 0)
-- Dependencies: 195
-- Name: seq_mail_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_mail_id', 23, true);


--
-- TOC entry 2214 (class 0 OID 0)
-- Dependencies: 183
-- Name: seq_message_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_message_id', 44, true);


--
-- TOC entry 2215 (class 0 OID 0)
-- Dependencies: 191
-- Name: seq_public_message_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_public_message_id', 20, true);


--
-- TOC entry 2216 (class 0 OID 0)
-- Dependencies: 176
-- Name: seq_user_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_user_id', 24, true);


--
-- TOC entry 2187 (class 0 OID 16411)
-- Dependencies: 175
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY "user" (id, username, email, firstname, lastname, language, gender, password, salt, blocked, deleted, created_on, blocked_on, deleted_on, iusername, iemail, protected, avatar) FROM stdin;
20	sf	bar@example.org	Sebastian	Fedrau	de	male	6725753a690d4c3db087e5b7b2cb09d518ca80881fc3e65617568cc1ed3a8ffa	miadZsMZlW39vGyrWDezLcW1Mon8Jgdj	f	f	2016-01-11 14:37:55.105	\N	\N	sf	bar@example.org	f	dfc9c4108e6cf245b4e04a0d8a957e9c95ee1ceb30c9ea88359b3f7149f26121.png
21	fnord	fnord@example.org	\N	\N	\N	\N	996e784c389419c41003632558de2544a999f870995fb39c240b023a623c0171	UGjAskGJW0mbTG0fsINCLfGBAx97ytl6	f	f	2016-01-13 17:30:04.36	\N	\N	fnord	fnord@example.org	t	\N
23	baz	baz@example.org	\N	\N	\N	\N	322961ccf2f357c328bd76be8b2fffdb48aaa74ee82c5b9c24f0b181e6c574f9	iI8zLsfpZ3KArtKZcQFAP9iMnKnslv1c	f	t	2016-01-20 17:17:35.06	\N	2016-01-21 06:42:53.511	baz	baz@example.org	t	\N
24	snafu	snafu@example.org	\N	\N	\N	\N	8be3aca2d73fc73e4a4a11d1c5b2b2b62f37008dda922e219b8caac5225f9cc3	uj4JC7EfDiDtXsfYlmISw8Ud5myLdUo9	f	f	2016-01-21 06:49:40.238	\N	\N	snafu	snafu@example.org	t	\N
\.


--
-- TOC entry 2198 (class 0 OID 16786)
-- Dependencies: 186
-- Data for Name: user_favorite; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_favorite (object_guid, user_id, created_on) FROM stdin;
\.


--
-- TOC entry 2189 (class 0 OID 16444)
-- Dependencies: 177
-- Data for Name: user_friendship; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_friendship (user_id, friend_id) FROM stdin;
20	21
21	20
\.


--
-- TOC entry 2201 (class 0 OID 17127)
-- Dependencies: 193
-- Data for Name: user_recommendation; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_recommendation (object_guid, user_id, created_on, receiver_id) FROM stdin;
\.


--
-- TOC entry 2186 (class 0 OID 16403)
-- Dependencies: 174
-- Data for Name: user_request; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_request (request_id, request_code, username, email, created_on, iusername, iemail) FROM stdin;
\.


--
-- TOC entry 2034 (class 2606 OID 16822)
-- Name: password_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT password_request_unique_request_id UNIQUE (request_id);


--
-- TOC entry 2032 (class 2606 OID 16549)
-- Name: pk_message; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY message
    ADD CONSTRAINT pk_message PRIMARY KEY (id);


--
-- TOC entry 2020 (class 2606 OID 16465)
-- Name: pk_object; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object
    ADD CONSTRAINT pk_object PRIMARY KEY (guid);


--
-- TOC entry 2029 (class 2606 OID 17116)
-- Name: pk_object_comment; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT pk_object_comment PRIMARY KEY (id);


--
-- TOC entry 2022 (class 2606 OID 16470)
-- Name: pk_object_score; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT pk_object_score PRIMARY KEY (object_guid, user_id);


--
-- TOC entry 2025 (class 2606 OID 16487)
-- Name: pk_object_tag; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT pk_object_tag PRIMARY KEY (user_id, object_guid, tag);


--
-- TOC entry 2036 (class 2606 OID 16677)
-- Name: pk_password_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT pk_password_request_id PRIMARY KEY (request_id, request_code);


--
-- TOC entry 2041 (class 2606 OID 17086)
-- Name: pk_public_message; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY public_message
    ADD CONSTRAINT pk_public_message PRIMARY KEY (id);


--
-- TOC entry 2011 (class 2606 OID 16663)
-- Name: pk_request; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT pk_request PRIMARY KEY (request_id, request_code);


--
-- TOC entry 2039 (class 2606 OID 16790)
-- Name: pk_user_favorite; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT pk_user_favorite PRIMARY KEY (object_guid, user_id);


--
-- TOC entry 2018 (class 2606 OID 17054)
-- Name: pk_user_friendship; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT pk_user_friendship PRIMARY KEY (user_id, friend_id);


--
-- TOC entry 2015 (class 2606 OID 16434)
-- Name: pk_user_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT pk_user_id PRIMARY KEY (id);


--
-- TOC entry 2045 (class 2606 OID 17131)
-- Name: pk_user_recommendation; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT pk_user_recommendation PRIMARY KEY (object_guid, user_id, receiver_id);


--
-- TOC entry 2013 (class 2606 OID 16820)
-- Name: user_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT user_request_unique_request_id UNIQUE (request_id);


--
-- TOC entry 2026 (class 1259 OID 16527)
-- Name: fk_object_guid; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fk_object_guid ON object_comment USING btree (object_guid);


--
-- TOC entry 2027 (class 1259 OID 17088)
-- Name: fk_user_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fk_user_id ON object_comment USING btree (user_id);


--
-- TOC entry 2037 (class 1259 OID 16801)
-- Name: fki_favorite_user_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_favorite_user_id ON user_favorite USING btree (user_id);


--
-- TOC entry 2046 (class 1259 OID 32799)
-- Name: fki_mail_receiver_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_mail_receiver_id ON mail USING btree (receiver_id);


--
-- TOC entry 2042 (class 1259 OID 17148)
-- Name: fki_object_recommendation_receiver_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_object_recommendation_receiver_id ON user_recommendation USING btree (receiver_id);


--
-- TOC entry 2043 (class 1259 OID 17142)
-- Name: fki_object_recommendation_user_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_object_recommendation_user_id ON user_recommendation USING btree (user_id);


--
-- TOC entry 2023 (class 1259 OID 16812)
-- Name: fki_object_tag_object_guid; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_object_tag_object_guid ON object_tag USING btree (object_guid);


--
-- TOC entry 2030 (class 1259 OID 16555)
-- Name: fki_receiver_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_receiver_id ON message USING btree (receiver_id);


--
-- TOC entry 2016 (class 1259 OID 17055)
-- Name: fki_user_friendship_friendship_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_user_friendship_friendship_id ON user_friendship USING btree (friend_id);


--
-- TOC entry 2061 (class 2620 OID 16615)
-- Name: trg_check_user_request_username_and_email; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_check_user_request_username_and_email BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_username_and_email_are_unique();


--
-- TOC entry 2070 (class 2620 OID 24577)
-- Name: trg_object_comment_create_message; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_object_comment_create_message AFTER INSERT ON object_comment FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_comment_message();


--
-- TOC entry 2069 (class 2620 OID 17077)
-- Name: trg_object_score_create_message; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_object_score_create_message AFTER INSERT ON object_score FOR EACH ROW EXECUTE PROCEDURE trg_fn_generate_vote_messages();


--
-- TOC entry 2068 (class 2620 OID 16777)
-- Name: trg_object_update_timestamps; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_object_update_timestamps BEFORE UPDATE ON object FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_object_timestamps();


--
-- TOC entry 2062 (class 2620 OID 16628)
-- Name: trg_update_user_request_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_update_user_request_iusername_and_iemail BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- TOC entry 2063 (class 2620 OID 16618)
-- Name: trg_user_check_email; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_check_email BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_email_can_be_changed();


--
-- TOC entry 2071 (class 2620 OID 17151)
-- Name: trg_user_create_recommendation_message; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_create_recommendation_message BEFORE INSERT ON user_recommendation FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_recommendation_message();


--
-- TOC entry 2067 (class 2620 OID 16590)
-- Name: trg_user_friendship_destroyed; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_friendship_destroyed AFTER DELETE ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_destroy_friendship_message();


--
-- TOC entry 2066 (class 2620 OID 16589)
-- Name: trg_user_friendship_inserted; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_friendship_inserted AFTER INSERT ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_friendship_message();


--
-- TOC entry 2064 (class 2620 OID 16629)
-- Name: trg_user_update_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_update_iusername_and_iemail BEFORE INSERT OR UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- TOC entry 2065 (class 2620 OID 16670)
-- Name: trg_user_update_timestamps; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_update_timestamps BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_user_timestamps();


--
-- TOC entry 2054 (class 2606 OID 16550)
-- Name: fk_message_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY message
    ADD CONSTRAINT fk_message_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- TOC entry 2053 (class 2606 OID 17089)
-- Name: fk_object_comment_author_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_author_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 2052 (class 2606 OID 16522)
-- Name: fk_object_comment_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 2048 (class 2606 OID 16481)
-- Name: fk_object_score_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 2049 (class 2606 OID 16471)
-- Name: fk_object_score_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 2051 (class 2606 OID 16807)
-- Name: fk_object_tag_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 2050 (class 2606 OID 16802)
-- Name: fk_object_tag_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 2055 (class 2606 OID 16791)
-- Name: fk_user_favorite_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 2056 (class 2606 OID 16796)
-- Name: fk_user_favorite_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 2047 (class 2606 OID 17056)
-- Name: fk_user_friendship_friendship_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT fk_user_friendship_friendship_id FOREIGN KEY (friend_id) REFERENCES "user"(id);


--
-- TOC entry 2057 (class 2606 OID 17132)
-- Name: fk_user_recommendation_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 2058 (class 2606 OID 17143)
-- Name: fk_user_recommendation_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- TOC entry 2059 (class 2606 OID 17137)
-- Name: fk_user_recommendation_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_recommendation
    ADD CONSTRAINT fk_user_recommendation_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 2060 (class 2606 OID 32794)
-- Name: mail_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY mail
    ADD CONSTRAINT mail_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- TOC entry 2210 (class 0 OID 0)
-- Dependencies: 5
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2016-01-21 17:29:15

--
-- PostgreSQL database dump complete
--


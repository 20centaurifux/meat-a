--
-- PostgreSQL database dump
--

-- Dumped from database version 9.4.5
-- Dumped by pg_dump version 9.4.5
-- Started on 2016-01-13 07:45:53

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 185 (class 3079 OID 11855)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2137 (class 0 OID 0)
-- Dependencies: 185
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- TOC entry 573 (class 1247 OID 16731)
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
-- TOC entry 576 (class 1247 OID 16748)
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
-- TOC entry 203 (class 1255 OID 16617)
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
-- TOC entry 201 (class 1255 OID 16606)
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
-- TOC entry 206 (class 1255 OID 16583)
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
-- TOC entry 205 (class 1255 OID 16584)
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
-- TOC entry 198 (class 1255 OID 16626)
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
-- TOC entry 208 (class 1255 OID 16775)
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
-- TOC entry 204 (class 1255 OID 16632)
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
-- TOC entry 202 (class 1255 OID 16636)
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
-- TOC entry 207 (class 1255 OID 16671)
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
-- TOC entry 200 (class 1255 OID 16635)
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
-- TOC entry 199 (class 1255 OID 16682)
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
-- TOC entry 181 (class 1259 OID 16528)
-- Name: seq_message_id; Type: SEQUENCE; Schema: public; Owner: meat-a
--

CREATE SEQUENCE seq_message_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE seq_message_id OWNER TO "meat-a";

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 182 (class 1259 OID 16543)
-- Name: message; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE message (
    id integer DEFAULT nextval('seq_message_id'::regclass) NOT NULL,
    receiver_id integer NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    read_status boolean DEFAULT false NOT NULL,
    read_on timestamp without time zone,
    target character varying(64) NOT NULL,
    type message_type NOT NULL,
    source character varying(64) NOT NULL
);


ALTER TABLE message OWNER TO "meat-a";

--
-- TOC entry 176 (class 1259 OID 16449)
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
-- TOC entry 180 (class 1259 OID 16491)
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
-- TOC entry 179 (class 1259 OID 16488)
-- Name: object_comment; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE object_comment (
    id integer DEFAULT nextval('seq_comment_id'::regclass) NOT NULL,
    parent_id integer,
    author_id integer NOT NULL,
    object_guid uuid NOT NULL,
    comment_text character varying(4096) NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    deleted boolean DEFAULT false NOT NULL,
    deleted_on timestamp without time zone
);


ALTER TABLE object_comment OWNER TO "meat-a";

--
-- TOC entry 177 (class 1259 OID 16466)
-- Name: object_score; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE object_score (
    object_guid uuid NOT NULL,
    user_id integer NOT NULL,
    up boolean NOT NULL
);


ALTER TABLE object_score OWNER TO "meat-a";

--
-- TOC entry 178 (class 1259 OID 16477)
-- Name: object_tag; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE object_tag (
    user_id integer NOT NULL,
    object_guid uuid NOT NULL,
    tag character varying(32) NOT NULL
);


ALTER TABLE object_tag OWNER TO "meat-a";

--
-- TOC entry 183 (class 1259 OID 16672)
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
-- TOC entry 174 (class 1259 OID 16431)
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
-- TOC entry 173 (class 1259 OID 16411)
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
-- TOC entry 184 (class 1259 OID 16786)
-- Name: user_favorite; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE user_favorite (
    object_guid uuid NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE user_favorite OWNER TO "meat-a";

--
-- TOC entry 175 (class 1259 OID 16444)
-- Name: user_friendship; Type: TABLE; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE TABLE user_friendship (
    user_id integer NOT NULL,
    friend_id integer NOT NULL
);


ALTER TABLE user_friendship OWNER TO "meat-a";

--
-- TOC entry 172 (class 1259 OID 16403)
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
-- TOC entry 2127 (class 0 OID 16543)
-- Dependencies: 182
-- Data for Name: message; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY message (id, receiver_id, created_on, read_status, read_on, target, type, source) FROM stdin;
\.


--
-- TOC entry 2121 (class 0 OID 16449)
-- Dependencies: 176
-- Data for Name: object; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object (guid, source, created_on, deleted, deleted_on, reported, reported_on, locked, locked_on) FROM stdin;
25ceff6e-3626-4a50-aaba-fa90b18b7984	foo	2016-01-12 18:08:55.994	f	\N	f	\N	f	\N
5e9c9ffe-d4c3-4c1a-987e-42ee560990e0	bar	2016-01-12 18:18:17.548	t	2016-01-12 18:29:55.355	f	\N	f	\N
\.


--
-- TOC entry 2124 (class 0 OID 16488)
-- Dependencies: 179
-- Data for Name: object_comment; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_comment (id, parent_id, author_id, object_guid, comment_text, created_on, deleted, deleted_on) FROM stdin;
\.


--
-- TOC entry 2122 (class 0 OID 16466)
-- Dependencies: 177
-- Data for Name: object_score; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_score (object_guid, user_id, up) FROM stdin;
\.


--
-- TOC entry 2123 (class 0 OID 16477)
-- Dependencies: 178
-- Data for Name: object_tag; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY object_tag (user_id, object_guid, tag) FROM stdin;
\.


--
-- TOC entry 2128 (class 0 OID 16672)
-- Dependencies: 183
-- Data for Name: password_request; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY password_request (request_id, request_code, user_id, created_on) FROM stdin;
\.


--
-- TOC entry 2138 (class 0 OID 0)
-- Dependencies: 180
-- Name: seq_comment_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_comment_id', 1, false);


--
-- TOC entry 2139 (class 0 OID 0)
-- Dependencies: 181
-- Name: seq_message_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_message_id', 7, true);


--
-- TOC entry 2140 (class 0 OID 0)
-- Dependencies: 174
-- Name: seq_user_id; Type: SEQUENCE SET; Schema: public; Owner: meat-a
--

SELECT pg_catalog.setval('seq_user_id', 20, true);


--
-- TOC entry 2118 (class 0 OID 16411)
-- Dependencies: 173
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY "user" (id, username, email, firstname, lastname, language, gender, password, salt, blocked, deleted, created_on, blocked_on, deleted_on, iusername, iemail, protected, avatar) FROM stdin;
20	sf	bar@example.org	Sebastian	Fedrau	de	male	6725753a690d4c3db087e5b7b2cb09d518ca80881fc3e65617568cc1ed3a8ffa	miadZsMZlW39vGyrWDezLcW1Mon8Jgdj	f	f	2016-01-11 14:37:55.105	\N	\N	sf	bar@example.org	f	dfc9c4108e6cf245b4e04a0d8a957e9c95ee1ceb30c9ea88359b3f7149f26121.png
\.


--
-- TOC entry 2129 (class 0 OID 16786)
-- Dependencies: 184
-- Data for Name: user_favorite; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_favorite (object_guid, user_id) FROM stdin;
\.


--
-- TOC entry 2120 (class 0 OID 16444)
-- Dependencies: 175
-- Data for Name: user_friendship; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_friendship (user_id, friend_id) FROM stdin;
\.


--
-- TOC entry 2117 (class 0 OID 16403)
-- Dependencies: 172
-- Data for Name: user_request; Type: TABLE DATA; Schema: public; Owner: meat-a
--

COPY user_request (request_id, request_code, username, email, created_on, iusername, iemail) FROM stdin;
\.


--
-- TOC entry 1983 (class 2606 OID 16822)
-- Name: password_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT password_request_unique_request_id UNIQUE (request_id);


--
-- TOC entry 1981 (class 2606 OID 16549)
-- Name: pk_message; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY message
    ADD CONSTRAINT pk_message PRIMARY KEY (id);


--
-- TOC entry 1968 (class 2606 OID 16465)
-- Name: pk_object; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object
    ADD CONSTRAINT pk_object PRIMARY KEY (guid);


--
-- TOC entry 1978 (class 2606 OID 16509)
-- Name: pk_object_comment; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT pk_object_comment PRIMARY KEY (id);


--
-- TOC entry 1970 (class 2606 OID 16470)
-- Name: pk_object_score; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT pk_object_score PRIMARY KEY (object_guid, user_id);


--
-- TOC entry 1973 (class 2606 OID 16487)
-- Name: pk_object_tag; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT pk_object_tag PRIMARY KEY (user_id, object_guid, tag);


--
-- TOC entry 1985 (class 2606 OID 16677)
-- Name: pk_password_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY password_request
    ADD CONSTRAINT pk_password_request_id PRIMARY KEY (request_id, request_code);


--
-- TOC entry 1959 (class 2606 OID 16663)
-- Name: pk_request; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT pk_request PRIMARY KEY (request_id, request_code);


--
-- TOC entry 1988 (class 2606 OID 16790)
-- Name: pk_user_favorite; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT pk_user_favorite PRIMARY KEY (object_guid, user_id);


--
-- TOC entry 1966 (class 2606 OID 16448)
-- Name: pk_user_friendship; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT pk_user_friendship PRIMARY KEY (user_id, friend_id);


--
-- TOC entry 1963 (class 2606 OID 16434)
-- Name: pk_user_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT pk_user_id PRIMARY KEY (id);


--
-- TOC entry 1961 (class 2606 OID 16820)
-- Name: user_request_unique_request_id; Type: CONSTRAINT; Schema: public; Owner: meat-a; Tablespace: 
--

ALTER TABLE ONLY user_request
    ADD CONSTRAINT user_request_unique_request_id UNIQUE (request_id);


--
-- TOC entry 1974 (class 1259 OID 16515)
-- Name: fki_author_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_author_id ON object_comment USING btree (author_id);


--
-- TOC entry 1986 (class 1259 OID 16801)
-- Name: fki_favorite_user_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_favorite_user_id ON user_favorite USING btree (user_id);


--
-- TOC entry 1975 (class 1259 OID 16527)
-- Name: fki_object_guid; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_object_guid ON object_comment USING btree (object_guid);


--
-- TOC entry 1971 (class 1259 OID 16812)
-- Name: fki_object_tag_object_guid; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_object_tag_object_guid ON object_tag USING btree (object_guid);


--
-- TOC entry 1976 (class 1259 OID 16521)
-- Name: fki_parent_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_parent_id ON object_comment USING btree (parent_id);


--
-- TOC entry 1979 (class 1259 OID 16555)
-- Name: fki_receiver_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_receiver_id ON message USING btree (receiver_id);


--
-- TOC entry 1964 (class 1259 OID 16818)
-- Name: fki_user_friendship_friendship_id; Type: INDEX; Schema: public; Owner: meat-a; Tablespace: 
--

CREATE INDEX fki_user_friendship_friendship_id ON user_friendship USING btree (friend_id);


--
-- TOC entry 2000 (class 2620 OID 16615)
-- Name: trg_check_user_request_username_and_email; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_check_user_request_username_and_email BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_username_and_email_are_unique();


--
-- TOC entry 2007 (class 2620 OID 16777)
-- Name: trg_object_update_timestamps; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_object_update_timestamps BEFORE UPDATE ON object FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_object_timestamps();


--
-- TOC entry 2001 (class 2620 OID 16628)
-- Name: trg_update_user_request_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_update_user_request_iusername_and_iemail BEFORE INSERT OR UPDATE ON user_request FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- TOC entry 2002 (class 2620 OID 16618)
-- Name: trg_user_check_email; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_check_email BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_check_if_email_can_be_changed();


--
-- TOC entry 2006 (class 2620 OID 16590)
-- Name: trg_user_friendship_destroyed; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_friendship_destroyed AFTER DELETE ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_destroy_friendship_message();


--
-- TOC entry 2005 (class 2620 OID 16589)
-- Name: trg_user_friendship_inserted; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_friendship_inserted AFTER INSERT ON user_friendship FOR EACH ROW EXECUTE PROCEDURE trg_fn_create_friendship_message();


--
-- TOC entry 2003 (class 2620 OID 16629)
-- Name: trg_user_update_iusername_and_iemail; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_update_iusername_and_iemail BEFORE INSERT OR UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_iusername_and_iemail();


--
-- TOC entry 2004 (class 2620 OID 16670)
-- Name: trg_user_update_timestamps; Type: TRIGGER; Schema: public; Owner: meat-a
--

CREATE TRIGGER trg_user_update_timestamps BEFORE UPDATE ON "user" FOR EACH ROW EXECUTE PROCEDURE trg_fn_update_user_timestamps();


--
-- TOC entry 1997 (class 2606 OID 16550)
-- Name: fk_message_receiver_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY message
    ADD CONSTRAINT fk_message_receiver_id FOREIGN KEY (receiver_id) REFERENCES "user"(id);


--
-- TOC entry 1994 (class 2606 OID 16510)
-- Name: fk_object_comment_author_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_author_id FOREIGN KEY (author_id) REFERENCES "user"(id);


--
-- TOC entry 1995 (class 2606 OID 16522)
-- Name: fk_object_comment_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 1996 (class 2606 OID 16516)
-- Name: fk_object_comment_parent_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_comment
    ADD CONSTRAINT fk_object_comment_parent_id FOREIGN KEY (parent_id) REFERENCES object_comment(id);


--
-- TOC entry 1990 (class 2606 OID 16481)
-- Name: fk_object_score_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 1991 (class 2606 OID 16471)
-- Name: fk_object_score_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_score
    ADD CONSTRAINT fk_object_score_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 1993 (class 2606 OID 16807)
-- Name: fk_object_tag_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 1992 (class 2606 OID 16802)
-- Name: fk_object_tag_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY object_tag
    ADD CONSTRAINT fk_object_tag_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 1998 (class 2606 OID 16791)
-- Name: fk_user_favorite_object_guid; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_object_guid FOREIGN KEY (object_guid) REFERENCES object(guid);


--
-- TOC entry 1999 (class 2606 OID 16796)
-- Name: fk_user_favorite_user_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_favorite
    ADD CONSTRAINT fk_user_favorite_user_id FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- TOC entry 1989 (class 2606 OID 16813)
-- Name: fk_user_friendship_friendship_id; Type: FK CONSTRAINT; Schema: public; Owner: meat-a
--

ALTER TABLE ONLY user_friendship
    ADD CONSTRAINT fk_user_friendship_friendship_id FOREIGN KEY (friend_id) REFERENCES "user"(id);


--
-- TOC entry 2136 (class 0 OID 0)
-- Dependencies: 5
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2016-01-13 07:45:54

--
-- PostgreSQL database dump complete
--


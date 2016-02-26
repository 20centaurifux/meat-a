.SUFFIXES: .m4 .sql

CONFIG_FILE=../config.py
M4_DEFS=-DUSER_REQUEST_TIMEOUT=`grep USER_REQUEST_TIMEOUT $(CONFIG_FILE) | awk '{{print $$3}}'` \
        -DPASSWORD_REQUEST_TIMEOUT=`grep PASSWORD_REQUEST_TIMEOUT $(CONFIG_FILE) | awk '{{print $$3}}'`
TARGETS=triggers.sql maintenance.sql

%.sql: %.m4
	m4 $(M4_DEFS) $< > $@

all: $(TARGETS)

clean:
	rm -fr $(TARGETS)

PYLINT_DISABLED_WARNINGS := relative-import,missing-docstring,fixme,star-args,too-many-lines,locally-disabled,too-few-public-methods,too-many-ancestors,no-self-use,duplicate-code --ignored-classes=SQLObject,scoped_session,RelationshipProperty
PYLINT_GOOD_NAMES := "_,i,j,k,d,f,s,x,ex,Run,pw,service_GET,service_POST,id,Base,logger,sf"
PYLINT_OPTS := -rn -d $(PYLINT_DISABLED_WARNINGS) --good-names=$(PYLINT_GOOD_NAMES)
PYLINT := pylint $(PYLINT_OPTS)

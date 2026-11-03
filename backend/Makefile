PY ?= python3
BEHAVE = $(PY) -m behave
BEHAVE_ALLURE = -f pretty -o - -f allure -o allure-results

.PHONY: features feature tags unit test report cli dto

features:            ## run every BDD scenario
	$(BEHAVE)

feature:             ## run one feature: make feature name=credit_gap
	$(BEHAVE) features/$(name).feature

tags:                ## run a tag slice: make tags tag=@more-cash
	$(BEHAVE) --tags=$(tag)

unit:                ## pytest unit tests (support library, model invariants)
	$(PY) -m pytest

test: unit features  ## everything

report:              ## behave + Allure 3 report (needs: npm install -g allure)
	rm -rf allure-results allure-report
	$(BEHAVE) $(BEHAVE_ALLURE) || true
	allure generate -c .allurerc.mjs -o allure-report
	allure open allure-report

cli:                 ## reference properties report
	$(PY) cli.py

dto:                 ## regenerate app/models/input_fields.py from proto/sincero/simulation_input.proto (needs grpcio-tools)
	$(PY) tools/gen_dto.py

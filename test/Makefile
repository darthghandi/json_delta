PYTHON27='python3'
SH='bash'

.PHONY: all
all: endtoend python

.PHONY: Material
Material: cases.json targets.json diffs.json udiffs.json
	$(PYTHON27) -c 'import test_jig; test_jig.write_out_data()'
	$(PYTHON27) -c 'import test_jig, os; test_jig.write_out_data(os.path.join(test_jig.DOTDOT, "python", "test", "Material"))'

.PHONY: endtoend
endtoend:
	$(PYTHON27) test_jig.py -v

.PHONY: python
python: Material
	PYTHON27=$(PYTHON27) $(SH) native_python_tests.sh

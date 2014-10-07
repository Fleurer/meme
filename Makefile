test:
	nosetests -s

benchmark:
	python meme/benchmarks/trade_10000_orders.py

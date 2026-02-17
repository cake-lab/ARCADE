# Lighting Estimation Case Study: Xihe

How to build:

```bash
docker build -t expar-case-study-xihe .
```

How to run:

```bash
docker run --rm \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/outputs:/app/outputs \
  expar-case-study-xihe

```

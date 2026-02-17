# Case Study Examples

See [xihe](./xihe) as an example.

External programs can be packaged into Docker containers to be used in ARCADE.

In your Dockerfile, you should provide path for both inputs and outputs. For example:

```Dockerfile
# Create expected input/output directories
RUN mkdir -p /app/inputs /app/outputs
VOLUME ["/app/inputs", "/app/outputs"]
```

# The OpenModelica image is the base: the compiler and runtime are the whole reason this
# needs a server at all. The model is compiled during the build so a request costs ~0.3 s
# rather than the tens of seconds a compile takes.
FROM openmodelica/openmodelica:v1.27.1-ompython

WORKDIR /app

RUN pip install --no-cache-dir --break-system-packages \
      fastapi==0.136.3 uvicorn[standard]==0.41.0 numpy

COPY sim/ /app/sim/
COPY model/ /app/model/
COPY api/ /app/api/

# Compile once, into the image.
RUN mkdir -p /app/build && cd /app/build && \
    printf 'loadFile("/app/model/RideThroughCore.mo"); getErrorString();\nbuildModel(RideThroughCore, startTime=0, stopTime=15.0, numberOfIntervals=4000, method="dassl", tolerance=1e-6, outputFormat="csv");\ngetErrorString();\n' > build.mos && \
    omc build.mos && \
    test -x /app/build/RideThroughCore

# The binary is native here, so the runner executes it directly instead of shelling out
# to a container as it does on macOS.
ENV GR1D_NATIVE=1
ENV PYTHONPATH=/app

EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]

"""Silence LiteLLM's optional-provider noise.

LiteLLM pre-loads the response shapes for every provider it supports when it is
first imported, and logs a WARNING for each one it cannot load. On a machine
without `botocore` that is two lines about Bedrock and SageMaker on every single
run:

    17:10:36 - LiteLLM:WARNING: common_utils.py:979 - litellm: could not
    pre-load bedrock-runtime response stream shape ...

Nothing in DCIT 403 uses Bedrock or SageMaker, and the warning says nothing about
our Groq or Gemini calls, so it is noise in every transcript we keep as evidence.
This module raises the log level of LiteLLM's loggers to ERROR and nothing else:
real errors are still printed, warnings about providers we do not use are not.

    from quiet_litellm import quiet_litellm
    quiet_litellm()          # call this *before* the first litellm import
"""

import logging


def quiet_litellm() -> None:
    """Raise LiteLLM's log level to ERROR for every one of its loggers."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    # LiteLLM also logs through child loggers such as "LiteLLM.Info"; a level set
    # on the parent does not stop a child record, so lift those too.
    for name, logger in list(logging.root.manager.loggerDict.items()):
        if name.startswith("LiteLLM") and isinstance(logger, logging.Logger):
            logger.setLevel(logging.ERROR)

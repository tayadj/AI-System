import src.core
import src.model
import src.data
import string
import pandas
import torch
import sys
import os
import re

def BuildScript(model_version, data_version):

    data = src.data.load(data_version)

    match data_version:

        case 'alpha':

            data_validation_pipeline = src.core.pipeline.DataValidationPipeline({'version': 'alpha'})
            data_clean = data_validation_pipeline.process(data['data'])

            model_embedding_pipeline = src.core.pipeline.ModelEmbeddingPipeline({'version': 'alpha'})
            data_loader = model_embedding_pipeline.process(data_clean)

            engine = src.core.Engine()
            model = engine.produce('alpha')

            model_training_pipeline = src.core.pipeline.ModelTrainingPipeline(model, data_loader, {'version': 'alpha'})
            model_training_pipeline.train()

            config = {'version': 'alpha', 'message_length': model_embedding_pipeline.message_length}
            environment = {'encoder' : model_embedding_pipeline.encoder}

            src.model.save(model_training_pipeline.model, environment, config)
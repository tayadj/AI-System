import src.core
import src.model
import string
import pandas
import torch
import sys
import os
import re



class ModelInferencePipeline:

	def __init__(self, version):

		self.data = src.model.load(version)

		self.engine = src.core.Engine()
		self.model = self.engine.produce(version)
		self.model.load_state_dict(self.data['model'])
		self.model.eval()

	def preprocess(self, text):

		match self.data['config'].get('version'):

			case "sequential" | "transformer":

				text = re.sub(r'([{}])'.format(re.escape(string.punctuation)), r' \1 ', text)
				text = re.sub(r'\s+', ' ', text).strip()
				text = re.sub(r'<[^>]+>', '', text)
				text = re.sub(r'\[\d+\]|&#91;\d+&#93;', '', text)
				text = re.sub(r'&#\d+;', '', text)
				text = re.sub(r'\s+', ' ', text)
				text = text.strip()
				text = text.lower()

		return text

	# delete preprocess and move its functionality to process??
	# implement alpha model inference

	def process(self, sample):

		match self.data['config'].get('version'):

			case 'alpha':

				data_validation_pipeline = src.core.pipeline.DataValidationPipeline({'version': 'alpha'})
				sample['message'] = sample['message'].map(data_validation_pipeline.validate)

				encoder = self.data['environment'].get('encoder')
				message_length = self.data['config'].get('message_length')

				input = []

				for record in sample['message']:

					message_tensor = encoder.transform(record.split())

					if len(message_tensor) < message_length:

						message_tensor = torch.cat([torch.tensor(message_tensor, dtype = torch.long), torch.zeros(message_length - len(message_tensor), dtype = torch.long)])

					else:

						message_tensor = torch.tensor(message_tensor[:message_length], dtype = torch.long)

					input.append(message_tensor)

				return self.model.predict(torch.stack(input, dim = 0))

			case "sequential" | "transformer":

				self.model.load_state_dict(self.data['model'])
				self.model.eval()

				dvp_config = self.data['config'].get('dvp_config')

				for attribute in sample.columns:

					if attribute not in dvp_config.get('exclude'):

						sample[attribute] = sample[attribute].map(str)
						sample[attribute] = sample[attribute].map(self.preprocess)

					if attribute in dvp_config.get('time'):

						sample[attribute] = pandas.to_datetime(sample[attribute], format='%Y-%m-%d')

				encoder_gender = self.data['environment'].get('encoder_gender')
				encoder_location = self.data['environment'].get('encoder_location')
				encoder_category = self.data['environment'].get('encoder_category')

				current_date = pandas.to_datetime('today')
				sample['subject_age'] = sample['subject_birth'].apply(lambda value: current_date.year - value.year - ((current_date.month, current_date.day) < (value.month, value.day)))
				sample['subject_gender'] = encoder_gender.transform(sample['subject_gender'])
				sample['subject_location'] = encoder_location.transform(sample['subject_location'])
				sample['object_category'] = encoder_category.transform(sample['object_category'])

				input = {
					'subject_id': torch.tensor(sample['subject_id'], dtype=torch.long),
					'subject_gender': torch.tensor(sample['subject_gender'], dtype=torch.long),
					'subject_age': torch.tensor(sample['subject_age'], dtype=torch.float),
					'subject_location': torch.tensor(sample['subject_location'], dtype=torch.long),
					'object_id': torch.tensor(sample['object_id'], dtype=torch.long),
					'object_category': torch.tensor(sample['object_category'], dtype=torch.long),
				}

				with torch.no_grad():

					prediction = self.model.predict(input)
				
				return prediction

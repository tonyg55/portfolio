from fastapi import FastAPI, HTTPException
import pandas as pd
import numpy as np
import pickle
import json
import os


app = FastAPI(title = 'Purchase Prediction API')


@app.post("/predict")
def predict(data):
    model_name = 'model.pkl'
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, model_name)

        with open(file_path, 'rb') as file:
            model = pickle.load(file)

        data = json.loads(data)

        predictions_list = []
        variables_dict = model.params.to_dict()
        variables_dict_sorted = dict(sorted(variables_dict.items()))
        predicted_class_list = []

        if isinstance(data, list):  # Batch request by checking if data is a list
            for item in data:
                data_df = pd.DataFrame(item, index=[0], dtype=float)
                # Get the prediction probabilities
                predictions = model.predict(data_df)
                predictions_list.append(predictions.tolist())
                # Get the phat by calculating the 75th percentile of the predicted probabilities 
                # as specified by business partner
                cutoff = np.percentile(predictions, 75)
                # Apply the cutoff to get the predicted class
                predicted_class = (predictions >= cutoff).astype(int)
                predicted_class_list.append(predicted_class.tolist())
        else:  # Single request
            data_df = pd.DataFrame(data, index=[0], dtype=float)
            predictions = model.predict(data_df)
            predictions_list.append(predictions.tolist())
            cutoff = np.percentile(predictions, 75)
            predicted_class = (predictions >= cutoff).astype(int)
            predicted_class_list.append(predicted_class.tolist())

        # Return the predicted class, predicted probability, and model input variables
        output = {
            "business_outcome": predicted_class_list,
            "phat": predictions_list,
            "variables": variables_dict_sorted
        }
        print("******* MADE IT HERE 6")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"No model found in {file_path}")
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=str(e))

    return output # FastAI automatically serializes the output and returns it as a json object

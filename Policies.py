import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np
from matplotlib import pyplot as plt
tf.keras.backend.set_floatx('float64')

class SpgAgent(keras.models.Model):

    def __init__(self, SPG_network, training_param, data_logger, buffer):
        super(SpgAgent, self).__init__()
        self.model = SPG_network
        self.training_param = training_param
        self.data_logger = data_logger
        self.buffer = buffer


    def train_step(self):
        """
        Train at each timestep in the episode sampling uniformly from the batch
        """
        # TODO combine train_step and train_batch!
        # Sample mini-batch from memory
        batch = self.buffer.get_training_samples(self.training_param["batch_size"])
        states = np.array([each[0] for each in batch])
        actions = np.array([each[1] for each in batch])
        rewards = np.array([each[2] for each in batch])
        next_states = np.array([each[3] for each in batch])
        # TODO test next_states vs states
        with tf.GradientTape() as tape:
            # Calculate expected value from rewards
            # - At each timestep what was the total reward received after that timestep
            # - Rewards in the past are discounted by multiplying them with gamma
            # - These are the labels for our critic
            # Return = SUM_t=0^inf (gamma*reward_t)
            eps = np.finfo(np.float32).eps.item()  # Smallest number such that 1.0 + eps != 1.0
            gamma = self.training_param["gamma"]

            timesteps, states, rewards, chosen_actions = self.data_logger.get_experience()

            action_probs, critic_value = self.model(states)

            actions = []
            for t in range(len(timesteps)):
                actions.append(action_probs[t, chosen_actions[t]])
            actions = tf.convert_to_tensor(actions)
            actor_log_prob = tf.math.log(actions)

            returns = []
            discounted_sum = 0
            for r in rewards[::-1]:
                discounted_sum = r + gamma * discounted_sum
                returns.insert(0, discounted_sum)

            # Normalize
            returns = np.array(returns)
            returns = (returns - np.mean(returns)) / (np.std(returns) + eps)
            returns = returns.tolist()
            self.data_logger.returns = returns

            # Calculating loss values to update our network
            history = zip(actor_log_prob, critic_value, returns)
            actor_losses = []
            critic_losses = []
            for actor_log_prob, crit_value, ret in history:
                # At this point in history, the critic estimated that we would get a
                # total reward = `value` in the future. We took an action with log probability
                # of `log_prob` and ended up receiving a total reward = `ret`.
                # The actor must be updated so that it predicts an action that leads to
                # high rewards (compared to critic's estimate) with high probability.
                diff = ret - crit_value
                self.data_logger.advantage.append(diff)
                actor_losses.append(-actor_log_prob * diff)  # actor loss

                # The critic must be updated so that it predicts a better estimate of
                # the future rewards.
                critic_losses.append(
                    self.training_param["loss_func"](tf.expand_dims(crit_value, 0), tf.expand_dims(ret, 0))
                )

            # Backpropagation
            loss_value = sum(actor_losses) + sum(critic_losses)
            self.data_logger.losses.append(loss_value)
            grads = tape.gradient(loss_value, self.model.trainable_variables)
            self.data_logger.gradients.append(grads)
            self.training_param["optimiser"].apply_gradients(zip(grads, self.model.trainable_variables))
            # Clear the loss and reward history
    

    def train_batch(self):
        """
        Train all experiences obtained during an episode
        """
        with tf.GradientTape() as tape:
            # Calculate expected value from rewards
            # - At each timestep what was the total reward received after that timestep
            # - Rewards in the past are discounted by multiplying them with gamma
            # - These are the labels for our critic
            # Return = SUM_t=0^inf (gamma*reward_t)
            eps = np.finfo(np.float32).eps.item()  # Smallest number such that 1.0 + eps != 1.0
            gamma = self.training_param["gamma"]

            timesteps, states, rewards, chosen_actions = self.data_logger.get_experience()

            action_probs, critic_value = self.model(states)

            actions = []
            for t in range(len(timesteps)):
                actions.append(action_probs[t, chosen_actions[t]])
            actions = tf.convert_to_tensor(actions)
            actor_log_prob = tf.math.log(actions)

            returns = []
            discounted_sum = 0
            for r in rewards[::-1]:
                discounted_sum = r + gamma * discounted_sum
                returns.insert(0, discounted_sum)

            # Normalize
            returns = np.array(returns)
            returns = (returns - np.mean(returns)) / (np.std(returns) + eps)
            returns = returns.tolist()
            self.data_logger.returns = returns

            # Calculating loss values to update our network
            history = zip(actor_log_prob, critic_value, returns)
            actor_losses = []
            critic_losses = []
            for actor_log_prob, crit_value, ret in history:
                # At this point in history, the critic estimated that we would get a
                # total reward = `value` in the future. We took an action with log probability
                # of `log_prob` and ended up receiving a total reward = `ret`.
                # The actor must be updated so that it predicts an action that leads to
                # high rewards (compared to critic's estimate) with high probability.
                diff = ret - crit_value
                self.data_logger.advantage.append(diff)
                actor_losses.append(-actor_log_prob * diff)  # actor loss

                # The critic must be updated so that it predicts a better estimate of
                # the future rewards.
                critic_losses.append(
                    self.training_param["loss_func"](tf.expand_dims(crit_value, 0), tf.expand_dims(ret, 0))
                )

            # Backpropagation
            loss_value = sum(actor_losses) + sum(critic_losses)
            self.data_logger.losses.append(loss_value)
            grads = tape.gradient(loss_value, self.model.trainable_variables)
            self.data_logger.gradients.append(grads)
            self.training_param["optimiser"].apply_gradients(zip(grads, self.model.trainable_variables))
            # Clear the loss and reward history




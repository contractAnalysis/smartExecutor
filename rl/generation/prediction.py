def my_model_prediction(model, env, num_episodes, flag_maskable:bool=True):

  result_list=[]
  for i in range(num_episodes):
      obs, _ = env.reset()
      while not env.done:
          if flag_maskable:
              action_masks = env.action_masks()
              action, _states = model.predict(obs, action_masks=action_masks)
              # action, _states = model.predict(obs)
              obs, reward, done, _, info = env.step(action)
              # print(f'\taction:{action};reward:{reward};obs:{obs}')
          else:
              action, _states = model.predict(obs)
              obs, reward, done, _, info = env.step(action)

      if env.env_name is not None and env.env_name in [ "ContractEnv_55",]:
          # print(f'score:{env.score}')
          # print(f'\taction seq:{env.previous_actions}')
          # print(f'\t  func seq:{env.func_seq}')
          result_list.append([env.conEnvData_wsa["function_data"][str(func)]["name"] for func in env.func_seq])

      elif env.env_name in ["ContractEnv_33"]:

          # print(f'score:{env.score}')
          # print(f'\taction seq:{env.previous_actions}')
          result_list.append(
              [env.conEnvData_wsa["function_data"][str(func)]["name"] for func
               in env.previous_actions])


      else:
          return []

      if len(result_list)==num_episodes:
          break

  return result_list


def print_functions(function_data:dict,target_functions:list):
    for func_int, data in function_data.items():
        print(f'{func_int}: {data["pure_name"]}')
    print(f'targets:{target_functions}')

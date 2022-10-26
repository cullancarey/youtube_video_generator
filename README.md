# Youtube Video Generator

Welcome to my Youtube video generator project. This repository holds the code to my Python script that uploads videos to Youtube programmatically and tweets about the videos.

### Inspiration
I was looking to improve various areas of my skillset in this project and hit all my areas of interest. I wanted to create something I could share with friends and family! I was doing some research and came across [Sudeep Chauhan's](https://blog.sudcha.com/about) [blog post](https://sudcha.com/i-made-youtube-videos-using-python/) about automating the creation of Youtube videos, and I thought it was a great idea. At the end of the post, he specifies people are free to use it, so I wanted to see if I could tweak it and create my version of his idea.

### How it works

This program first scrapes Reddit r/quotes for the newest SFW post on the page. It then writes that quote to a text file and, using tts, creates an audio file of the quote. Next, it will do a google image search based on the text file to retrieve relevant images for the video. After that, it will create the video file using FFmpeg. Finally, it will call the upload_video.py file provided by Youtube [here](https://developers.google.com/youtube/v3/guides/uploading_a_video). The video will appear on my [Youtube channel](https://www.youtube.com/channel/UCGU6cW0iBDA0N3D6iHcc5zg) every day at 10 pm EST. 

The second part of the project tweets about the videos. It retrieves to most recent upload to the Youtube channel and tweets about the video to the [Twitter account](https://twitter.com/VideosByPython) I created for it. The tweets contain the video title, link to the Youtube channel, link directly to the video, and the exact time of the tweet. See an example [here](https://twitter.com/VideosByPython/status/1585318022528598016?cxt=HHwWgIC8zfKVl4AsAAAA).

### Code behind the magic

The project is completely serverless and hosted on AWS. The project leverages AWS services, including Lambda, S3, and Eventbridge rules. The infrastructure is controlled and maintained by Terraform. Please see the relevant directories below containing the code.

  - [Terraform](./terraform)
  - [Lambdas](./lambdas)

### Github Actions

I utilize Github Actions for my CI/CD implementation for this project. There are two workflows for this project:
1. [format_code.yml](./.github/workflows/format_code.yml)
  - This workflow is my CI part of the process. It uses two Python tools (Black and Pylint) to format my Python code. It also utilizes Checkov to ensure compliance with my Terraform code. 
2. [deploy.yml](./.github/workflows/deploy.yml)
  - This workflow is my CD part of the process. It builds the Lambda deployment packages and then deploys the Terraform to my AWS account.

### Final thoughts

This project was a lot of fun and a great learning experience. I greatly improved my Python skills and my DevOps and Cloud knowledge. I hope people enjoy the content. I am open to feedback on the code or other parts of the process. I plan to clean up the Python code more regarding code reuse and organizing the functions better. Please feel free to reach me at <cullancarey@gmail.com>.
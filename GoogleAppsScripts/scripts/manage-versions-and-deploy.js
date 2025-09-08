#!/usr/bin/env node

/**
 * Google Apps Script Version Management and Deployment Script
 * 
 * This script:
 * 1. Gets the current list of deployed versions
 * 2. Cleans up old versions if approaching the 200 limit
 * 3. Creates a new deployment
 * 4. Provides detailed logging for CI/CD
 */

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

const MAX_VERSIONS = 200;
const CLEANUP_THRESHOLD = 190; // Start cleanup when we have this many versions
const KEEP_RECENT_VERSIONS = 10; // Always keep the most recent N versions

class GASVersionManager {
  constructor(projectName) {
    this.projectName = projectName;
    this.projectInfo = null;
  }

  async log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
  }

  async runClaspCommand(command) {
    try {
      const { stdout, stderr } = await execAsync(`clasp ${command}`);
      if (stderr && !stderr.includes('warning')) {
        await this.log(`⚠️ Warning: ${stderr}`);
      }
      return stdout.trim();
    } catch (error) {
      await this.log(`❌ Error running 'clasp ${command}': ${error.message}`);
      throw error;
    }
  }

  async getProjectInfo() {
    if (!this.projectInfo) {
      try {
        const output = await this.runClaspCommand('status --json');
        this.projectInfo = JSON.parse(output);
      } catch (error) {
        await this.log(`❌ Failed to get project info: ${error.message}`);
        throw error;
      }
    }
    return this.projectInfo;
  }

  async getDeployments() {
    try {
      // Try with --json flag first (newer clasp versions)
      const output = await this.runClaspCommand('deployments --json');
      const deployments = JSON.parse(output);
      return deployments || [];
    } catch (jsonError) {
      // Fallback for older clasp versions without --json support
      try {
        await this.log(`⚠️ --json flag not supported, using fallback parsing`);
        const output = await this.runClaspCommand('deployments');
        const deployments = this.parseDeploymentsOutput(output);
        return deployments || [];
      } catch (fallbackError) {
        await this.log(`❌ Failed to get deployments: ${fallbackError.message}`);
        return [];
      }
    }
  }

  parseDeploymentsOutput(output) {
    // Parse the text output from older clasp versions
    // Example output: "- AKfycbx... @1" or "No deployments."
    const deployments = [];
    const lines = output.split('\n');
    
    for (const line of lines) {
      const match = line.match(/^-\s+([A-Za-z0-9_-]+)\s+@(\d+)/);
      if (match) {
        deployments.push({
          deploymentId: match[1],
          versionNumber: match[2]
        });
      }
    }
    
    return deployments;
  }

  async deleteDeployment(deploymentId) {
    try {
      await this.runClaspCommand(`undeploy ${deploymentId}`);
      await this.log(`🗑️ Deleted deployment: ${deploymentId}`);
      return true;
    } catch (error) {
      await this.log(`❌ Failed to delete deployment ${deploymentId}: ${error.message}`);
      return false;
    }
  }

  async cleanupOldVersions() {
    await this.log('🧹 Checking if version cleanup is needed...');
    
    const deployments = await this.getDeployments();
    const versionDeployments = deployments.filter(d => d.versionNumber && d.deploymentId);
    
    await this.log(`📊 Current deployments: ${versionDeployments.length}`);
    
    if (versionDeployments.length < CLEANUP_THRESHOLD) {
      await this.log(`✅ No cleanup needed (${versionDeployments.length} < ${CLEANUP_THRESHOLD})`);
      return;
    }

    await this.log(`🚨 Cleanup needed! Current: ${versionDeployments.length}, Threshold: ${CLEANUP_THRESHOLD}`);
    
    // Sort by version number (oldest first)
    versionDeployments.sort((a, b) => parseInt(a.versionNumber) - parseInt(b.versionNumber));
    
    // Calculate how many to delete
    const targetVersionCount = MAX_VERSIONS - 20; // Leave buffer for new deployment
    const toDelete = versionDeployments.length - targetVersionCount;
    
    if (toDelete <= 0) {
      await this.log('✅ No versions need to be deleted');
      return;
    }

    await this.log(`🗑️ Need to delete ${toDelete} old versions`);
    
    // Delete oldest versions, but keep the most recent KEEP_RECENT_VERSIONS
    const toDeleteList = versionDeployments.slice(0, Math.max(0, versionDeployments.length - KEEP_RECENT_VERSIONS - (targetVersionCount - toDelete)));
    
    let deletedCount = 0;
    let failedCount = 0;

    for (const deployment of toDeleteList.slice(0, toDelete)) {
      const success = await this.deleteDeployment(deployment.deploymentId);
      if (success) {
        deletedCount++;
      } else {
        failedCount++;
      }
      
      // Add small delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    await this.log(`📊 Cleanup complete: ${deletedCount} deleted, ${failedCount} failed`);
    
    if (failedCount > 0) {
      await this.log(`⚠️ Warning: ${failedCount} deployments could not be deleted`);
    }
  }

  async createDeployment() {
    await this.log('🚀 Creating new deployment...');
    
    try {
      // Generate deployment description
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const gitCommit = process.env.GITHUB_SHA ? process.env.GITHUB_SHA.substring(0, 7) : 'local';
      const description = `Auto-deploy ${timestamp} (${gitCommit})`;
      
      const output = await this.runClaspCommand(`deploy --description "${description}"`);
      
      // Parse deployment ID from output
      const deploymentMatch = output.match(/- (AKfycb[a-zA-Z0-9_-]+)/);
      const versionMatch = output.match(/Version (\d+)/);
      
      if (deploymentMatch && versionMatch) {
        const deploymentId = deploymentMatch[1];
        const versionNumber = versionMatch[1];
        
        await this.log(`✅ Deployment successful!`);
        await this.log(`🏷️ Version: ${versionNumber}`);
        await this.log(`🆔 Deployment ID: ${deploymentId}`);
        
        // Get project info to show web app URL
        const projectInfo = await this.getProjectInfo();
        if (projectInfo.scriptId) {
          const webAppUrl = `https://script.google.com/macros/s/${deploymentId}/exec`;
          await this.log(`🌐 Web App URL: ${webAppUrl}`);
        }
        
        return {
          success: true,
          deploymentId,
          versionNumber,
          description
        };
      } else {
        await this.log(`⚠️ Deployment may have succeeded, but couldn't parse output: ${output}`);
        return { success: true, output };
      }
    } catch (error) {
      await this.log(`❌ Deployment failed: ${error.message}`);
      throw error;
    }
  }

  async run() {
    try {
      await this.log(`🚀 Starting deployment process for: ${this.projectName}`);
      
      // Validate clasp setup
      await this.log('🔍 Validating clasp setup...');
      const status = await this.runClaspCommand('status');
      await this.log(`📋 Project status: ${status}`);
      
      // Clean up old versions if needed
      await this.cleanupOldVersions();
      
      // Create new deployment
      const result = await this.createDeployment();
      
      await this.log(`🎉 Deployment process completed successfully for: ${this.projectName}`);
      return result;
      
    } catch (error) {
      await this.log(`💥 Deployment process failed for ${this.projectName}: ${error.message}`);
      process.exit(1);
    }
  }
}

// Main execution
async function main() {
  const projectName = process.env.PROJECT_NAME || process.cwd().split('/').pop();
  const manager = new GASVersionManager(projectName);
  await manager.run();
}

if (require.main === module) {
  main().catch(error => {
    console.error('💥 Fatal error:', error);
    process.exit(1);
  });
}

module.exports = GASVersionManager;
